# Copyright 2020 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import re
from datetime import datetime, timedelta
from jinja2 import Template
from typing import Dict, Tuple, List, Optional
from config import Config
from github.IssueComment import IssueComment
from github.Repository import Repository
from fcp_timers import FCPTimers

log = logging.getLogger(__name__)


class CommandHandler(object):
    """Processes and handles issue comments that contain commands"""

    def __init__(self, config: Config, repo: Repository):
        self.config = config
        self.repo = repo
        self.COMMANDS = {
            self._command_fcp: ["fcp"],
            self._command_review: ["review", "reviewed"],
            self._command_concern: ["concern"],
            self._command_resolve: ["resolve", "resolved"],
        }
        self.github_fcp_proposal_template = Template(
            open(config.github_fcp_proposal_template_path).read(), autoescape=True
        )
        self.proposal = None
        self.comment = None
        self.proposal_labels_str = []
        self.team_vote_regex = re.compile(r"^- \[x\] @(.+)$", re.IGNORECASE)

        # Set up FCP timer handler, and callback functions
        self.fcp_timers = FCPTimers(
            config.fcp_timer_json_filepath, self._on_fcp_timer_fired
        )

    def handle_comment(self, comment: Dict):
        # Check for any commands
        commands = self.parse_commands_from_text(comment["comment"]["body"])

        # Retrieve the issue this comment is attached to
        self.proposal = self.repo.get_issue(comment["issue"]["number"])
        self.proposal_labels_str = [label["name"] for label in comment["issue"]["labels"]]
        original_labels = self.proposal_labels_str.copy()

        self.comment = comment

        log.debug("ACTION: %s", comment["action"])

        # Check if this is a new comment or an edit
        if comment["action"] == "edited":
            # Check if this is an edit of a status comment
            if self.comment["comment"]["body"].startswith("Team member @"):
                # Process status comment update
                self._process_status_comment_update()
            else:
                # Otherwise ignore
                return

        # Run command functions
        for command in commands:
            name, parameters = command
            for command_function, command_names in self.COMMANDS.items():
                if name in command_names:
                    # We found a matching function, run it with given parameters
                    command_function(parameters)

        # Check if the proposal labels have changed during processing
        if self.proposal_labels_str != original_labels:
            # If so, update them on the server
            self.proposal.set_labels(*self.proposal_labels_str)

    def parse_commands_from_text(self, text: str) -> List[Tuple[str, List[str]]]:
        """Extract any bot commands from a comment

        Returns:
            A list of tuples containing (command name, list of command parameters)
        """
        commands = []
        lines = text.split("\\n")

        # Read each line of the comment and check if it starts with @<botname>
        for line in lines:
            words = line.split()
            first_word = words.pop(0)
            if first_word == "@" + self.config.github_user.login:
                command = words[0]
                parameters = words[1:]
                commands.append((command, parameters))

        return commands

    def _command_fcp(self, parameters: List[str]):
        """Kick off an FCP with a given disposition"""
        disposition = parameters.pop(0)

        if disposition == "cancel":
            # Check that this proposal is in FCP
            if self.config.github_fcp_label not in self.proposal_labels_str:
                self._post_comment(
                    "This proposal is not in FCP."
                )
                return

            self._cancel_fcp()
            return

        if disposition not in ["merge", "postpone", "close"]:
            self._post_comment(f"Unknown disposition '{disposition}'.")
            return

        if self.config.github_fcp_proposed_label in self.proposal_labels_str:
            self._post_comment("An FCP proposal is already in progress.")
            return

        # Propose FCP
        self._fcp_proposal_with_disposition(disposition)

    def _command_review(
        self,
        parameters: List[str]
    ):
        """Mark an in-FCP proposal as reviewed by the commenter"""
        pass

    def _command_concern(
        self,
        parameters: List[str]
    ):
        """Raise a concern on an in-FCP proposal"""
        pass

    def _command_resolve(self, parameters: List[str]):
        """Resolve an existing concern on an in-FCP proposal"""
        pass

    def _fcp_proposal_with_disposition(self, disposition: str):
        """Propose an FCP with a given disposition"""
        # Ensure this proposal is not already in FCP
        if self.config.github_fcp_label in self.proposal_labels_str:
            self._post_comment("This proposal is already in FCP.")
            return

        # Ensure this proposal is not already in FCP-proposed
        if self.config.github_fcp_proposed_label in self.proposal_labels_str:
            self._post_comment("This proposal has already had a FCP proposed. Please "
                               "cancel the current one first.")
            return

        # Calculate team_votes content
        team_votes = self._format_team_votes(self.comment["sender"]["login"])

        comment_text = self.github_fcp_proposal_template.render(
            comment_author=self.comment["sender"]["login"],
            disposition=disposition,
            team_votes=team_votes,
        )

        self._post_comment(comment_text)

        # Add the relevant label
        if disposition == "merge":
            self.proposal_labels_str.append(self.config.github_disposition_merge_label)
        elif disposition == "postpone":
            self.proposal_labels_str.append(self.config.github_disposition_postpone_label)
        elif disposition == "close":
            self.proposal_labels_str.append(self.config.github_disposition_close_label)

        # Add the proposal label
        self.proposal_labels_str.append(self.config.github_fcp_proposed_label)

    def _process_status_comment_update(self):
        """Process an edit on a status comment. Checks to see if the required
        threshold of voters have been met for an FCP proposal.
        """
        log.debug("Processing status comment edit...")

        num_team_votes = len(self._parse_team_votes_from_comment(self.comment))
        num_team_members = len([m for m in self.config.github_team.get_members()])
        
        # Check if more than 75% of people have voted
        if num_team_votes / num_team_members < 0.75:
            return

        # Check that this proposal isn't already in FCP
        if self.config.github_fcp_label in self.proposal_labels_str:
            log.warning("FCP attempted to start on a proposal that was already in FCP")
            return

        # Start FCP
        self._start_fcp()

    def _start_fcp(self):
        """Begin an FCP. Start a timer"""
        # Calculate when this FCP should conclude
        fcp_conclusion_time = datetime.now() + timedelta(days=self.config.fcp_time_days)
        self.fcp_timers.new_timer(fcp_conclusion_time, self.proposal.number)

        # Post a comment stating that FCP has begun
        # TODO: Final comment period jinja2 template
        self._post_comment(
            ":bell: This is now entering its final comment period, "
            "as per the review above. :bell:"
        )

        # Add the FCP label
        self.proposal_labels_str.append(self.config.github_fcp_label)

        # Remove the FCP proposal label
        self.proposal_labels_str.remove(self.config.github_fcp_proposed_label)

    def _get_team_votes(self, comments: List[IssueComment]) -> str:
        """Retrieve the votes for the current FCP proposal"""
        # Iterate through all comments of the proposal
        # Check for an existing status comment
        # Is FCP currently proposed?
        if self.config.github_fcp_proposed_label in self.proposal_labels_str:
            # Find the latest status comment
            existing_status_comment = None
            for comment in reversed(comments):
                if comment.body.startswith("Team member @"):
                    existing_status_comment = comment
                    break

            if not existing_status_comment:
                return "Could not retrieve team vote count"

            # Retrieve existing team votes
            log.info("Parsing comment: %s", existing_status_comment)
            team_votes = self._parse_team_votes_from_comment(existing_status_comment)

        # Has it been proposed before? If FCP proposed label was removed before,
        # only get comments since then

    def _parse_team_votes_from_comment(self, comment: Dict) -> List[str]:
        """Retrieves the users who have currently voted for FCP using the body of a
        given comment and cross-references them with the members of the github team

        Returns:
            A list of github usernames which have voted
        """
        voted_members = []
        for line in comment["comment"]["body"].split("\n"):
            match = self.team_vote_regex.match(line)
            if match:
                member = match.group(1)
                voted_members.append(member)

        return voted_members

    def _format_team_votes(self, voted_members: List[str]) -> str:
        """Given a list of members who have already voted, return a str list of
        who has an hasn't voted"""
        vote_text = ""
        for team_member in self.config.github_team.get_members():
            if team_member.login in voted_members:
                vote_text += "- [x] @lolfake" + team_member.login + "\n"
            else:
                vote_text += "- [ ] @lolfake" + team_member.login + "\n"

        return vote_text

    def _get_concerns(self, comments: List[IssueComment]) -> List[Tuple[str, bool]]:
        """Retrieve a list of any concerns on this proposal

        Returns:
            A list of concern tuples containing: (concern text, resolved)
        """
        # TODO:
        return []

    def _format_concerns(self, concerns: List[Tuple[str, bool]]) -> str:
        """Take a list of concern tuples and return a markdown-formatted list.
        Concerns are listed with bullet points; resolved concerns are struck out. Ex:

        Concerns:

            * Concern that has not been resolved
            * ~~Concern that has been resolved~~
        """
        if not concerns:
            return ""

        # Sort by resolved status
        concerns.sort(key=lambda x: x[1], reverse=True)

        text = "Concerns:\n\n"
        for concern, resolved in concerns:
            if resolved:
                text += "* %s"
            else:
                text += "* ~~%s~~"

            text = text % concern

        return text

    def _cancel_fcp(self):
        """Cancel FCP"""
        if self.config.github_fcp_label not in self.proposal_labels_str:
            self._post_comment("This proposal is not in FCP.")
            return

        # Remove the FCP label
        self.proposal_labels_str.remove(self.config.github_fcp_label)

        # Remove the FCP timer
        self.fcp_timers.cancel_timer_for_proposal_num(self.proposal.number)

        self._post_comment("Final comment period for this proposal has been cancelled.")

    # TODO: Abstract into the github_bot class
    def _post_or_update_status_comment(self, comment: Dict, text: str):
        """Post or edit an existing status comment on a proposal"""
        # Check for an existing status comment
        pass

    def _post_comment(self, text: str) -> Optional[IssueComment]:
        """Post a comment with the given text to a proposal

        Returns:
            The posted comment, or None if posting failed
        """
        truncated_text = text.split("\n")[0] + "..."
        comment = self.proposal.create_comment(text)
        log.info(
            f"Posted comment to issue #{self.proposal.number} with text {truncated_text}"
        )
        return comment

    # TODO: All of this should go in a github_client class
    def _on_fcp_timer_fired(self, proposal_num: int):
        # Retrieve the proposal object of this proposal
        self.proposal = self.repo.get_issue(proposal_num)
        self.proposal_labels_str = [label.name for label in self.proposal.get_labels()]

        # Enact the disposition specified by the proposal labels
        self._enact_disposition()

        # Update labels
        self.proposal.set_labels(*self.proposal_labels_str)

    def _enact_disposition(self):
        """Enact a disposition on a proposal, defined by the current disposition label
        of the proposal
        """
        # Figure out which disposition to enact
        for label in self.proposal_labels_str:
            disposition_label = label
            if label == self.config.github_disposition_merge_label:
                self._merge_proposal()
                break
            elif label == self.config.github_disposition_close_label:
                self._close_proposal()
                break
            elif label == self.config.github_disposition_postpone_label:
                self._postpone_proposal()
                break
        else:
            log.error(f"Attempted to enact a disposition on a proposal without a valid "
                      f"disposition label. Proposal labels: {self.proposal_labels_str}")
            return

        # Remove the FCP label
        self.proposal_labels_str.remove(self.config.github_fcp_label)

        # Remove the disposition label
        if disposition_label:
            self.proposal_labels_str.remove(disposition_label)

    def _merge_proposal(self):
        # TODO: Merge the proposal. Has to be done with git
        self._post_comment(
            "The final comment period, with a disposition to **merge**, as per "
            "the review above, is now **complete**."
        )

    def _close_proposal(self):
        self._post_comment(
            "The final comment period, with a disposition to **close**, as per "
            "the review above, is now **complete**."
        )
        self.proposal.edit(state="closed")

    def _postpone_proposal(self):
        self._post_comment(
            "The final comment period, with a disposition to **postpone**, as per "
            "the review above, is now **complete**."
        )

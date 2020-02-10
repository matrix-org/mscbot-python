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
from jinja2 import Template
from typing import Dict, Tuple, List, Optional
from config import Config
from storage import Storage
from github.IssueComment import IssueComment
from github.Label import Label
from github.Repository import Repository

log = logging.getLogger(__name__)


class CommandHandler(object):
    """Processes and handles issue comments that contain commands"""

    def __init__(self, config: Config, repo: Repository):
        self.config = config
        self.repo = repo
        self.COMMANDS = {
            ["fcp"]: self._command_fcp,
            ["review", "reviewed"]: self._command_review,
            ["concern"]: self._command_concern,
            ["resolve", "resolved"]: self._command_resolve,
        }
        self.github_fcp_proposal_template = Template(
            open(config.github_fcp_proposal_template_path).read(), autoescape=True
        )
        self.proposal = None
        self.comment = None
        self.proposal_labels = []
        self.team_vote_regex = re.compile("^- \[x\] @(.+)$", re.IGNORECASE)

    def handle_comment(self, comment: Dict):
        # Check for any commands
        commands = self._parse_commands_from_text(comment["comment"]["body"])
        if not commands:
            return

        # Retrieve the issue this comment is attached to
        self.proposal = self.repo.get_issue(comment["issue"]["number"])
        self.proposal_labels = comment["issue"]["labels"]
        original_labels = self.proposal_labels.copy()

        self.comment = comment

        # Run command functions
        for command in commands:
            name, parameters = command
            for command_names, command_function in self.COMMANDS.items():
                if name in command_names:
                    # We found a matching function, run it with given parameters
                    command_function(parameters)

        # Check if the proposal labels have changed during processing
        if self.proposal_labels != original_labels:
            # Update the labels
            self.proposal.set_labels(self.proposal_labels)

    def _parse_commands_from_text(self, text: str) -> List[Tuple[str, List[str]]]:
        """Extract any bot commands from a comment

        Returns:
            A list of tuples containing (command name, list of command parameters)
        """
        commands = []
        lines = text.split("\n")

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
            if not self.config.github_fcp_label in self.proposal_labels:
                self._post_comment(
                    "This proposal is not in FCP."
                )
                return

            self._attempt_to_cancel_fcp_on_proposal()
            return

        if disposition not in ["merge", "postpone", "close"]:
            self._post_comment(f"Unknown disposition '{disposition}'")
            return

        self._attempt_disposition(disposition)

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

    def _attempt_disposition(self, disposition: str):
        """Attempt to enact a disposition on a proposal"""
        # Ensure this proposal is not already in FCP
        if self.config.github_fcp_label in self.proposal_labels:
            self._post_comment("This proposal is already in FCP.")
            return

        # Ensure this proposal is not already in FCP-proposed
        if self.config.github_fcp_proposed_label in self.proposal_labels:
            self._post_comment("This proposal has already had a FCP proposed. Please "
                               "cancel the current one first.")
            return

        # Retrieve all comments for this proposal
        comments = [c for c in self.proposal.get_comments()]

        # Calculate team_votes content
        team_votes = self._get_team_votes(comments)

        # Calculate concern content
        concerns = self._get_concerns(comments)
        concern_text = self._format_concerns(concerns)

        comment_text = self.github_fcp_proposal_template.render(
            comment_author=self.comment["sender"]["login"],
            disposition=disposition,
            team_votes=team_votes,
            concerns=concern_text,
        )

        self._post_comment(comment_text)

        # Add the relevant label
        label_to_add = None  # type: Optional[Label]
        if disposition == "merge":
            pass
        elif disposition == "postpone":
            pass
        elif disposition == "close":
            pass

        # Remove the proposal label
        self.proposal_labels.remove(self.config.github_fcp_proposed_label)

    def _get_team_votes(self, comments: List[IssueComment]) -> str:
        """Retrieve the votes for the current FCP proposal"""
        # Iterate through all comments of the proposal
        # Check for an existing status comment
        # Is FCP currently proposed?
        if self.config.github_fcp_proposed_label in self.proposal_labels:
            # Find the latest status comment
            existing_status_comment = None
            for comment in reversed(comments):
                if comment.body.startswith("Team member @"):
                    existing_status_comment = comment
                    break

            if not existing_status_comment:
                return "Could not retrieve team vote count"

            # Retrieve existing team votes
            team_votes = self._parse_team_votes_from_comment(existing_status_comment)
        else:


        # Has it been proposed before? If FCP proposed label was removed before,
        # only get comments since then

    def _parse_team_votes_from_comment(self, comment: IssueComment) -> List[str]:
        """Retrieves the users who have currently voted for FCP using the body of a
        given comment and cross-references them with the members of the github team

        Returns:
            A list of github usernames which have voted
        """
        voted_members = []
        for line in comment.body.split("\n"):
            match = self.team_vote_regex.match(line)
            if match:
                member = match.group(1)
                voted_members.append(member)

        return voted_members

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

    def _attempt_to_cancel_fcp_on_proposal(self) -> bool:
        """Attempt to cancel FCP on a proposal specified by its number

        Returns:
            Whether the cancellation was successful
        """
        if not self.config.github_fcp_label in self.proposal_labels:
            self._post_comment("This proposal is not in FCP.")

        # TODO
        return True

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

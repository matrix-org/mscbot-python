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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from github.IssueComment import IssueComment
from github.PaginatedList import PaginatedList
from github.Repository import Repository
from jinja2 import Template

from config import Config
from fcp_timers import FCPTimers
from storage import Storage

log = logging.getLogger(__name__)


class CommandHandler(object):
    """Processes and handles issue comments that contain commands"""

    def __init__(self, config: Config, store: Storage, repo: Repository):
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
        self.comment_link = None
        self.proposal_labels_str = []
        self.team_vote_regex = re.compile(r"^[*|-] \[x\] @(.+)$", re.IGNORECASE)
        self.resolved_concern_regex = re.compile(r"^[*|-] ~~(.+)~~.*")

        # Set up FCP timer handler, and callback functions
        self.fcp_timers = FCPTimers(store, self._on_fcp_timer_fired)

    def handle_comment(self, comment: Dict):
        # Replace any instances of \r\n with just \n
        comment["comment"]["body"] = comment["comment"]["body"].replace("\r\n", "\n")

        # Check for any commands
        commands = self.parse_commands_from_text(comment["comment"]["body"])

        # Retrieve the issue this comment is attached to
        # Account for issue and pull request review comments
        issue = comment["issue"] if "issue" in comment else comment["pull_request"]
        self.proposal = self.repo.get_issue(issue["number"])
        self.proposal_labels_str = [label["name"] for label in issue["labels"]]
        original_labels = self.proposal_labels_str.copy()

        self.comment = comment
        self.comment_link = comment["comment"]["html_url"]

        # Check if this is a new comment or an edit
        comment_body = self.comment["comment"]["body"]
        if comment["action"] == "edited":
            # Check if this is an edit of a status comment
            known_status_comment = self._get_status_comment()
            if (
                not known_status_comment
                or comment["comment"]["id"] != known_status_comment.id
            ):
                log.debug("Ignoring edit of non-status comment")
                return

            # Process status comment update
            self._process_status_comment_update_with_body(comment_body)
        else:
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
        lines = text.split("\n")

        # Read each line of the comment and check if it starts with @<botname>
        for line in lines:
            words = line.split()
            if not words:
                # Account for empty lines
                continue

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

    def _command_review(self, parameters: List[str]):
        """Mark an in-FCP proposal as reviewed by the commenter"""
        # Ensure that this proposal is in FCP proposed state
        if self.config.github_fcp_proposed_label not in self.proposal_labels_str:
            self._post_comment(
                "This proposal has not had an FCP proposed, so you cannot review it."
            )
            return

        # Get the current votes for this proposal
        status_comment = self._get_status_comment()
        if not status_comment:
            self._post_comment("Unable to find the status comment for this proposal...")
            return

        # Get the current votes for this proposal
        voted_members = self._parse_team_votes_from_status_comment_body(
            status_comment.body
        )

        # Mark the commenter as reviewed
        commenter = self.comment["sender"]["login"]
        if commenter not in voted_members:
            voted_members.append(commenter)

        # Update the status comment
        self._post_or_update_status_comment(
            voted_members=voted_members, existing_status_comment=status_comment
        )

    def _command_concern(self, parameters: List[str]):
        """Add a concern to the existing status comment"""
        # Get the existing status comment
        status_comment = self._get_status_comment()

        if not status_comment:
            self._post_comment(
                "Unable to add concern. Is this msc in FCP-proposed state?"
            )

        # Add concern to status comment
        concern_text = " ".join(parameters)
        self._add_concern_to_status_comment(status_comment, concern_text)

    def _command_resolve(self, parameters: List[str]):
        """Resolve an existing concern on an in-FCP proposal"""
        # Get the existing status comment
        status_comment = self._get_status_comment()

        if not status_comment:
            self._post_comment(
                "Unable to resolve concern. Is this msc in FCP-proposed state?"
            )

        # Resolve concern on status comment
        concern_text = " ".join(parameters)
        self._resolve_concern_on_status_comment(status_comment, concern_text)

        # Update status comment body, and check if this allows an FCP to occur
        self._process_status_comment_update_with_body(status_comment.body)

    def _add_concern_to_status_comment(
        self,
        status_comment: IssueComment,
        concern_text: str,
    ):
        """Add a concern to an existing status comment if it doesn't already exist"""
        # Get the current concerns
        concerns = self._parse_concerns_from_status_comment_body(status_comment.body)

        # Check that this concern hasn't already been raised
        for text, resolved in concerns:
            if concern_text == text:
                self._post_comment("That concern has already been raised.")
                return

        # Add this concern as unresolved
        concerns.append((concern_text, False))

        # Update the status comment
        self._post_or_update_status_comment(
            concerns=concerns, existing_status_comment=status_comment
        )

        # Add the concern label if it doesn't already exist
        if self.config.github_unresolved_concerns_label not in self.proposal_labels_str:
            self.proposal_labels_str.append(
                self.config.github_unresolved_concerns_label
            )

    def _resolve_concern_on_status_comment(
        self,
        status_comment: IssueComment,
        concern_text: str,
    ):
        """Resolves a concern on a status comment"""
        # Get the current concerns
        concerns = self._parse_concerns_from_status_comment_body(status_comment.body)

        # Check that this concern exists
        concern_index = -1
        for index, concern in enumerate(concerns):
            text, resolved = concern
            if concern_text == text:
                concern_index = index

        if concern_index == -1:
            # We didn't find the concern
            self._post_comment(f"Unknown concern '{concern_text}'.")
            return

        # Mark this concern as resolved
        concerns[concern_index] = (concern_text, True)

        # Update the status comment
        self._post_or_update_status_comment(
            concerns=concerns,
            existing_status_comment=status_comment,
        )

        # Check if all concerns have been resolved
        if all(resolved for _, resolved in concerns):
            # Remove the unresolved_concerns label
            if self.config.github_unresolved_concerns_label in self.proposal_labels_str:
                self.proposal_labels_str.remove(
                    self.config.github_unresolved_concerns_label
                )

    def _fcp_proposal_with_disposition(self, disposition: str):
        """Propose an FCP with a given disposition"""
        # Ensure this proposal is not already in FCP
        if self.config.github_fcp_label in self.proposal_labels_str:
            self._post_comment("This proposal is already in FCP.")
            return

        # Ensure this proposal is not already in FCP-proposed
        if self.config.github_fcp_proposed_label in self.proposal_labels_str:
            self._post_comment(
                "This proposal has already had a FCP proposed. Please "
                "cancel the current one first."
            )
            return

        # Post new status comment
        self._post_or_update_status_comment(
            voted_members=[self.comment["sender"]["login"]],
            concerns=[],
            disposition=disposition,
        )

        # Add the relevant disposition label
        if disposition == "merge":
            self.proposal_labels_str.append(self.config.github_disposition_merge_label)
        elif disposition == "postpone":
            self.proposal_labels_str.append(
                self.config.github_disposition_postpone_label
            )
        elif disposition == "close":
            self.proposal_labels_str.append(self.config.github_disposition_close_label)

        # Add the proposal label
        self.proposal_labels_str.append(self.config.github_fcp_proposed_label)

        # Remove proposal in review label if present
        if self.config.github_fcp_proposal_in_review_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(
                self.config.github_fcp_proposal_in_review_label
            )

        # Remove finished FCP label if present
        if self.config.github_fcp_finished_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(self.config.github_fcp_finished_label)

    def _process_status_comment_update_with_body(self, status_comment_body: str):
        """Process an edit on a status comment. Checks to see if the required
        threshold of voters have been met for an FCP proposal.
        """
        log.debug("Processing status comment edit...")

        num_team_votes = len(
            self._parse_team_votes_from_status_comment_body(status_comment_body)
        )
        num_team_members = self.config.github_team.get_members().totalCount

        # Check if more than 75% of people have voted
        team_vote_ratio = num_team_votes / num_team_members
        if team_vote_ratio < self.config.fcp_required_team_vote_ratio:
            log.debug(
                "Not enough votes to begin FCP %s/%s",
                team_vote_ratio,
                self.config.fcp_required_team_vote_ratio,
            )
            return

        # Prevent an FCP from starting if there are any unresolved concerns
        concerns = self._parse_concerns_from_status_comment_body(status_comment_body)
        unresolved_concerns = [c for c in concerns if c[1] is False]
        if unresolved_concerns:
            log.debug("Proposal has unresolved concerns: %s", unresolved_concerns)
            return

        # Check that this proposal isn't already in FCP
        if self.config.github_fcp_label in self.proposal_labels_str:
            log.warning("FCP attempted to start on a proposal that was already in FCP")
            return

        # Start FCP
        self._start_fcp()

    def _start_fcp(self):
        """Begin an FCP. Start a timer"""
        log.debug("Beginning FCP...")

        # Calculate when this FCP should conclude
        fcp_conclusion_time = (
            datetime.now(timezone.utc)
            + timedelta(days=self.config.fcp_time_days)
            + timedelta(seconds=10)
        )
        self.fcp_timers.new_timer(fcp_conclusion_time, self.proposal.number)

        # Link to the status comment
        status_comment = self._get_status_comment()

        # The conclusion time is formatted as July 14, 2022 at 14:34:14 UTC.
        comment_text = (
            f":bell: This is now entering its final comment period, "
            f"as per [the review]({status_comment.html_url}) above. :bell:"
            f"\n\nThe final comment period will run for {self.config.fcp_time_days} "
            f"days until {fcp_conclusion_time.strftime('%B %-d, %Y at %H:%M:%S %Z')}."
        )

        # Post a comment stating that FCP has begun
        # TODO: Final comment period jinja2 template
        self._post_comment(comment_text)

        # Add the FCP label
        self.proposal_labels_str.append(self.config.github_fcp_label)

        # Remove the FCP proposal label if present
        if self.config.github_fcp_proposed_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(self.config.github_fcp_proposed_label)

        # Remove the proposal in review label if present
        if self.config.github_fcp_proposal_in_review_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(
                self.config.github_fcp_proposal_in_review_label
            )

    def _get_status_comment(self) -> Optional[IssueComment]:
        """Retrieves an existing status comment for a proposal

        Returns:
            The status comment, or None if it cannot be found.
        """
        # Retrieve all of the comments for the proposal
        comments: PaginatedList = self.proposal.get_comments()

        # Find the latest status comment
        for comment in comments.reversed:
            if (
                comment.body.startswith("Team member @")
                and comment.user.login == self.config.github_user.login
            ):
                return comment

        return None

    def _parse_team_votes_from_status_comment_body(
        self, comment_body: str
    ) -> List[str]:
        """Retrieves the users who have currently voted for FCP using the body of a
        given comment and cross-references them with the members of the github team

        Returns:
            A list of github usernames which have voted
        """
        voted_members = []
        for line in comment_body.split("\n"):
            match = self.team_vote_regex.match(line)
            if match:
                member = match.group(1)
                voted_members.append(member)

        return voted_members

    def _parse_concerns_from_status_comment_body(
        self, comment_body: str
    ) -> List[Tuple[str, bool]]:
        """Retrieves the concerns and their resolved state from the body of a given
        status comment.
        """
        concern_tuples = []

        # We search for a list of concerns in the comment body, however
        # tagged members is also a list. We know the list of concerns will
        # come after a line starting with "concerns:", so ignore all list
        # items before that
        past_tagged_people_list = False
        for line in comment_body.split("\n"):
            # Check if we've passed the Concerns: bit of a status comment yet
            if line.lower().startswith("concerns:"):
                past_tagged_people_list = True
            if not past_tagged_people_list:
                continue

            # Check if this is a concern line
            if line.startswith("* ") or line.startswith("- "):
                # Check if this concern is resolved or not
                if line.startswith("* ~~") or line.startswith("- ~~"):
                    # Extract concern text from resolved concern
                    match = self.resolved_concern_regex.match(line)
                    if not match:
                        log.error(
                            "Unable to match a resolved concern ('%s') with our regex",
                            line,
                        )
                        continue

                    # Get the concern text from the regex match
                    concern_text = match.group(1)
                    concern_tuples.append((concern_text, True))
                else:
                    # Extract concern text from non-resolved concern
                    concern_tuples.append((line[2:], False))

        return concern_tuples

    def _format_team_votes(self, voted_members: List[str]) -> str:
        """Given a list of members who have already voted, return a str list of
        who has an hasn't voted"""
        vote_text = ""
        for team_member in self.config.github_team.get_members():
            if team_member.login in voted_members:
                vote_text += "- [x] @" + team_member.login + "\n"
            else:
                vote_text += "- [ ] @" + team_member.login + "\n"

        return vote_text

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
                text += f"* ~~{concern}~~\n"
            else:
                text += f"* {concern}\n"

        return text

    def _cancel_fcp(self):
        """Cancel FCP"""
        if self.config.github_fcp_proposed_label in self.proposal_labels_str:
            log.debug("Cancelling FCP proposal...")

            # Remove the FCP proposed label if present
            if self.config.github_fcp_proposed_label in self.proposal_labels_str:
                self.proposal_labels_str.remove(self.config.github_fcp_proposed_label)

            # Place a note on the current status comment declaring FCP proposal has been
            # cancelled
            status_comment = self._get_status_comment()
            if not status_comment:
                log.warning(
                    "Unable to find status comment of %s while cancelling an FCP proposal."
                    % (self.proposal.number,)
                )

            prepend_text = "**This FCP proposal has been cancelled by %s.**\n\n" % (
                self.comment_link,
            )

            self._post_or_update_status_comment(
                existing_status_comment=status_comment,
                text_to_prepend=prepend_text,
            )

        elif self.config.github_fcp_label in self.proposal_labels_str:
            log.debug("Cancelling FCP...")

            # Remove the FCP label if present
            if self.config.github_fcp_label in self.proposal_labels_str:
                self.proposal_labels_str.remove(self.config.github_fcp_label)

            # Remove the FCP timer
            self.fcp_timers.cancel_timer_for_proposal_num(self.proposal.number)

            self._post_comment(
                "Final comment period for this proposal has been cancelled."
            )

        else:
            self._post_comment("This proposal is not in FCP nor has had FCP proposed.")

        # Remove any disposition labels if present
        if self.config.github_disposition_close_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(self.config.github_disposition_close_label)
        if self.config.github_disposition_merge_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(self.config.github_disposition_merge_label)
        if self.config.github_disposition_postpone_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(
                self.config.github_disposition_postpone_label
            )

        # Add the proposal in review label back again
        self.proposal_labels_str.append(self.config.github_fcp_proposal_in_review_label)

    def _post_or_update_status_comment(
        self,
        voted_members: List[str] = None,
        concerns: List[Tuple[str, bool]] = None,
        disposition: str = None,
        existing_status_comment: IssueComment = None,
        text_to_prepend: str = None,
    ):
        """Post or edit an existing status comment on a proposal

        Args:
            voted_members: A list of users that have voted for this proposal
            concerns: A list of concern tuples, with concern_text, resolved
            existing_status_comment: If set, will edit this status comment instead of
                posting a new one
            text_to_prepend: If set, this text will be prepended to the status comment.
                Note that this will effectively render the comment as no longer
                detectable as a status comment, as the comment will not start with
                "Team member @... has proposed ..."
        """
        if (
            voted_members is None or concerns is None or disposition is None
        ) and existing_status_comment is None:
            log.error(
                "Attempted to auto-retrieve status comment values without providing"
                "a status comment. Proposal num: #%d",
                self.proposal.number,
            )
            return

        # Auto-retrieve certain values for convenience
        if voted_members is None:
            voted_members = self._parse_team_votes_from_status_comment_body(
                existing_status_comment.body
            )

        if concerns is None:
            concerns = self._parse_concerns_from_status_comment_body(
                existing_status_comment.body
            )

        if disposition is None:
            disposition = self._get_disposition()

        # Format voted members
        team_votes = self._format_team_votes(voted_members)

        # Format concerns
        concerns = self._format_concerns(concerns)

        # Set author for status comment. Use author of original comment if this is an update
        if existing_status_comment:
            author = existing_status_comment.user.login
        else:
            author = self.comment["sender"]["login"]

        comment_text = self.github_fcp_proposal_template.render(
            comment_author=author,
            disposition=disposition,
            team_votes=team_votes,
            concerns=concerns,
        )

        if text_to_prepend:
            comment_text = text_to_prepend + comment_text

        log.debug("Posting/updating status comment: %s", comment_text)

        if existing_status_comment:
            existing_status_comment.edit(comment_text)
        else:
            self._post_comment(comment_text)

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
        log.info("FCP for proposal %d has concluded", proposal_num)

        # Retrieve the proposal object of this proposal
        self.proposal = self.repo.get_issue(proposal_num)
        self.proposal_labels_str = [label.name for label in self.proposal.get_labels()]

        # Enact the disposition specified by the proposal labels
        self._enact_disposition()

        # Update labels
        self.proposal.set_labels(*self.proposal_labels_str)

    def _get_disposition(self) -> Optional[str]:
        """Get the current proposal disposition

        Returns:
            The disposition type, or None if no known disposition
        """
        for label in self.proposal_labels_str:
            if label == self.config.github_disposition_merge_label:
                return "merge"
            elif label == self.config.github_disposition_close_label:
                return "close"
            elif label == self.config.github_disposition_postpone_label:
                return "postpone"

        return None

    def _enact_disposition(self):
        """Enact a disposition on a proposal, defined by the current disposition label
        of the proposal
        """
        # Figure out which disposition to enact
        disposition = self._get_disposition()
        if not disposition:
            log.error(
                f"Attempted to enact a disposition on a proposal without a valid "
                f"disposition label. Proposal labels: {self.proposal_labels_str}"
            )
            return

        # Link to the status comment
        status_comment = self._get_status_comment()

        # TODO: Convert to enum
        if disposition == "merge":
            self._merge_proposal(status_comment.html_url)
            disposition_label = self.config.github_disposition_merge_label
        elif disposition == "close":
            self._close_proposal(status_comment.html_url)
            disposition_label = self.config.github_disposition_close_label
        else:
            self._postpone_proposal(status_comment.html_url)
            disposition_label = self.config.github_disposition_postpone_label

        # Remove the FCP label if present
        if self.config.github_fcp_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(self.config.github_fcp_label)

        # Add the "finished FCP" label
        self.proposal_labels_str.append(self.config.github_fcp_finished_label)

        # Remove the disposition label
        if disposition_label and disposition_label in self.proposal_labels_str:
            self.proposal_labels_str.remove(disposition_label)

    def _merge_proposal(self, status_comment_url: str):
        # TODO: Merge the proposal. Has to be done with git
        self._post_comment(
            f"The final comment period, with a disposition to **merge**, as per "
            f"[the review]({status_comment_url}) above, is now **complete**."
        )

    def _close_proposal(self, status_comment_url: str):
        self._post_comment(
            "The final comment period, with a disposition to **close**, as per "
            f"[the review]({status_comment_url}) above, is now **complete**."
        )
        self.proposal.edit(state="closed")

    def _postpone_proposal(self, status_comment_url: str):
        self._post_comment(
            "The final comment period, with a disposition to **postpone**, as per "
            f"[the review]({status_comment_url}) above, is now **complete**."
        )

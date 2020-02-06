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
from errors import ConfigError
from storage import Storage
from github import Github
from github.PaginatedList import PaginatedList
from github.Repository import Repository
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.GithubException import UnknownObjectException
from config import Config
from bot_commands import BotCommands

log = logging.getLogger(__name__)


class GithubScraper(object):
    """Downloads and stores/update the bot's current view of the proposals
    stored on a github repository

    """

    def __init__(self, config: Config, store: Storage, github: Github, repo: Repository):
        """
        Args:
            config: Bot configuration object
            store: Bot database storage object
            github: A github object to interact with the github API
            repo: A github repo
        """
        self.config = config
        self.store = store
        self.github = github
        self.repo = repo

        try:
            self.fcp_proposed_label = self.repo.get_label(
                self.config.github_fcp_proposed_label
            )
        except UnknownObjectException:
            raise ConfigError(
                f"Label '{self.config.github_fcp_proposed_label}' does not exist"
            )

    def scrape(self):
        """Scrape all github issues/prs for proposals and save them to the database"""
        log.info(f"Scraping proposals from {self.config.github_repo}")
        # Create a github label object
        proposal_label = self.repo.get_label(self.config.github_proposal_label)
        if not proposal_label:
            log.fatal(
                f"Unable to find github label {self.config.github_proposal_label}"
                f"on repository {self.config.github_repo}"
            )

        # Download proposal issues with that label
        proposals = self.repo.get_issues(labels=[proposal_label], state="all")

        # Store proposals in the database if they aren't already
        try:
            self._save_proposals(proposals)
        except Exception as e:
            log.error("Error storing proposal information: %s", e)

        log.info("Parsing proposal comments")

        # Download and parse comments of each proposal
        for proposal in proposals:
            if self.fcp_proposed_label not in proposal.labels:
                # This proposal is not in fcp proposed state
                continue

            try:
                self._save_fcp_proposed_state(proposal)
            except Exception as e:
                log.error("Error parsing proposal comments: %s", e)

    def _save_fcp_proposed_state(self, proposal: Issue):
        """Parse the comments of a proposal, storing the FCP proposal information
        """
        # Auto-commit once finished, back out changes if a failure occurs
        with self.store.conn:
            # Retrieve the comments from each proposal
            log.debug(
                f"Processing proposal in FCP-proposed state: '{proposal.title}'"
            )

            comments = proposal.get_comments()  # type: PaginatedList[IssueComment]

            # Convert PaginatedList to list that can be reversed
            comments_list = [c for c in comments]

            # Get comments from latest to earliest
            # Find FCP proposal comment
            for comment in reversed(comments_list):
                self._save_fcp_proposed_comment(comment)

    def _save_fcp_proposed_comment(self, comment: IssueComment):
        """Save a comment from a proposal in FCP-proposed state iff it contains
        information about or a command influencing the FCP proposal
        """
        # Check if this is a FCP state comment
        if comment.user.login == self.config.github_user.login:
            if comment.body.startswith("Team member @"):
                # This is an FCP proposal, store

                self.store.cur.execute("""
                    # Store who's done a tick
                    # Store what team this is a part of
                """)
        else:
            # Extract any commands from the comment
            commands = BotCommands.parse_commands_from_text(comment.body)

            # Act on any concern commands
            for command in commands:
                if command[0] == "concern":
                    # TODO: Calculate what concerns are in the comment already
                    pass

    def _save_proposals(self, proposals):
        """Save list of given proposals into the database

        Args:
            proposals (PaginatedList[Issue]): A list of proposals
        """
        # Auto-commit once finished, back out changes if a failure occurs
        with self.store.conn:
            # Delete current list of proposals
            # In case someone removes the proposal label from an issue, we don't want
            # to continue considering that issue a proposal
            self.store.cur.execute("DELETE FROM proposal")

            for proposal in proposals:
                log.debug(f"Saving proposal: {proposal.title}")

                # Extract labels into a storable state
                labels = []
                for label in proposal.labels:
                    labels.append(label.name)

                self.store.cur.execute("""
                    INSERT INTO proposal
                    (num, title, author, shepherd, labels)
                    VALUES
                    (%s, %s, %s, %s, %s)
                """, (
                    proposal.number,
                    proposal.title,
                    proposal.user.login,  # TODO: Ability to override author in issue text
                    None,  # TODO: Find shepherd from the issue text
                    labels,
                ))


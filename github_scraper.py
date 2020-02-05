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
from storage import Storage
from github import Github
from github.PaginatedList import PaginatedList
from github.Repository import Repository
from github.Issue import Issue
from config import Config

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

    def _save_proposals(self, proposals):
        """Save list of given proposals into the database

        Args:
            proposals (PaginatedList[Issue]): A list of proposals
        """
        # Auto-commit once finished, back out changes if a failure occurs
        with self.store.conn:
            for proposal in proposals:
                log.debug("Saving proposal: %s", proposal)

                # Extract labels into a storable state
                labels = []
                for label in proposal.labels:
                    labels.append(label.name)

                self.store.cur.execute("""
                    INSERT INTO proposal
                    (num, title, author, shepherd, labels)
                    VALUES
                    (%s, %s, %s, %s, %s)
                    ON CONFLICT
                        ON CONSTRAINT proposal_num
                    DO UPDATE SET
                        num = %s,
                        title = %s,
                        author = %s,
                        shepherd = %s,
                        labels = %s
                    WHERE proposal.num = %s
                """, (
                    proposal.number,
                    proposal.title,
                    proposal.user.login,  # TODO: Ability to override author in issue text
                    None,  # TODO: Find shepherd from the issue text
                    labels,

                    proposal.number,
                    proposal.title,
                    proposal.user.login,
                    None,
                    labels,

                    proposal.number,
                ))


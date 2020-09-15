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
import json
from typing import Dict
from github import Github
from github.Repository import Repository
from config import Config
from storage import Storage
from command_handler import CommandHandler
from github_webhook import Webhook
from flask import Flask

log = logging.getLogger(__name__)


class WebhookHandler(object):
    def __init__(
        self,
        config: Config,
        store: Storage,
        github: Github,
        repo: Repository,
    ):
        self.config = config
        self.github = github
        self.repo = repo
        self.command_handler = CommandHandler(config, store, repo)

        # Start a flash webserver
        self.app = Flask(__name__)

        webhook = Webhook(
            self.app,
            endpoint=self.config.webhook_path,
            secret=self.config.webhook_secret,
        )

        @self.app.route("/")
        def hello_world():
            return "Hello, world!"

        @webhook.hook("issue_comment")
        def on_issue_comment(data):
            log.debug(f"Got comment: {json.dumps(data, indent=4, sort_keys=True)}")
            self._process_comment(data)

        @webhook.hook("pull_request_review_comment")
        def on_pull_request_review_comment(data):
            log.debug(f"Got PR review comment: {json.dumps(data, indent=4, sort_keys=True)}")
            self._process_comment(data)

    def run(self):
        from waitress import serve
        serve(self.app, host=self.config.webhook_host, port=self.config.webhook_port)

    def _process_comment(self, comment: Dict):
        log.debug("Processing comment: %s", comment)

        comment_author = comment["sender"]
        comment_author_login = comment_author["login"]

        # Ignore comments/edits from ourselves
        if comment_author_login == self.config.github_user.login:
            log.debug("Ignoring comment from ourselves")
            return

        # Account for issue and pull request review comments
        issue = comment["issue"] if "issue" in comment else comment["pull_request"]

        # Check if this is a proposal
        if not self._issue_has_label(issue, self.config.github_proposal_label):
            log.debug("Ignoring comment without appropriate proposal label")
            return

        # Ignore comments from people who aren't on the team
        if not self._comment_belongs_to_team_member(comment):
            log.debug("Ignoring comment that doesn't belong to team member")
            return

        # Process any commands this comment contains
        self.command_handler.handle_comment(comment)

    def _issue_has_label(self, issue: Dict, label_name: str) -> bool:
        """Check whether a given issue has a label"""
        for label in issue["labels"]:
            if label["name"] == label_name:
                return True

        return False

    def _comment_belongs_to_team_member(self, comment: Dict) -> bool:
        """Return whether a comment was posted by a known team member"""
        author = comment["sender"]
        for member in self.config.github_team.get_members():
            if member.login == author["login"]:
                return True

        return False

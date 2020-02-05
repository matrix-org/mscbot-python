#!/usr/bin/env python
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


class GithubBot(object):
    """Bot functions to interface with github"""

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

    def post_comment(self, proposal: Issue, text: str):
        """Posts a comment to an issue"""

    def update_comment(self, comment):

    def parse_comment(self, text: str):
        """Parse an existing comment made by the bot

        Args:
            text: The text of the comment
        """
        # Figure out whether this is a FCP proposal comment



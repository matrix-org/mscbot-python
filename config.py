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
import os
import yaml
import sys
from typing import Optional
from errors import ConfigError
from github.Team import Team
from github.Organization import Organization

logger = logging.getLogger()


class Config(object):
    def __init__(self, filepath):
        """
        Args:
            filepath (str): Path to config file
        """
        self.github_team = None  # type: Optional[Team]
        self.github_org = None  # type: Optional[Organization]

        if not os.path.isfile(filepath):
            raise ConfigError(f"Config file '{filepath}' does not exist")

        # Load in the config file at the given filepath
        with open(filepath) as file_stream:
            config = yaml.safe_load(file_stream)

        # Logging setup
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s [%(levelname)s] %(message)s'
        )

        log_dict = config.get("logging", {})
        log_level = log_dict.get("level", "INFO")
        logger.setLevel(log_level)

        file_logging = log_dict.get("file_logging", {})
        file_logging_enabled = file_logging.get("enabled", False)
        file_logging_filepath = file_logging.get("filepath", "bot.log")
        if file_logging_enabled:
            handler = logging.FileHandler(file_logging_filepath)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        console_logging = log_dict.get("console_logging", {})
        console_logging_enabled = console_logging.get("enabled", True)
        if console_logging_enabled:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # Database setup
        database_dict = config.get("database", {})
        self.database_filepath = database_dict.get("postgres_path")

        # Github setup
        self.github_user = None  # Set later once we connect to github successfully

        github = config.get("github", {})
        self.github_access_token = github.get("access_token")
        if not self.github_access_token:
            raise ConfigError("github.access_token is required")

        self.github_repo = github.get("repo")
        if not self.github_repo:
            raise ConfigError("github.repo is required")

        self.github_proposal_label = github.get("proposal_label")
        if not self.github_proposal_label:
            raise ConfigError("github.proposal_label is required")
        self.github_fcp_proposed_label = github.get("fcp_proposed_label")
        if not self.github_fcp_proposed_label:
            raise ConfigError("github.fcp_proposed_label is required")
        self.github_fcp_label = github.get("fcp_label")
        if not self.github_fcp_label:
            raise ConfigError("github.fcp_label is required")

        self.github_fcp_proposal_template_path = github.get("fcp_proposal_template_path")
        if not self.github_fcp_proposal_template_path:
            raise ConfigError("github.fcp_proposal_template_path is required")

        self.github_org_name = github.get("org")
        if not self.github_org_name:
            raise ConfigError("github.org is required")
        self.github_team_name = github.get("team")
        if not self.github_team_name:
            raise ConfigError("github.team is required")

        # Webhook setup
        webhook = config.get("webhook", {})
        self.webhook_host = webhook.get("host", "0.0.0.0")
        self.webhook_port = webhook.get("port", 5050)
        self.webhook_secret = webhook.get("secret")

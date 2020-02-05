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
from errors import ConfigError

logger = logging.getLogger()


class Config(object):
    def __init__(self, filepath):
        """
        Args:
            filepath (str): Path to config file
        """
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
        github = config.get("github", {})
        self.github_access_token = github.get("access_token")
        if not self.github_access_token:
            raise ConfigError("github.access_token is required")

        self.github_proposal_label = github.get("proposal_label")
        if not self.github_proposal_label:
            raise ConfigError("github.proposal_label is required")

        self.github_repo = github.get("repo")
        if not self.github_repo:
            raise ConfigError("github.repo is required")
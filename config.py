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
from typing import Optional, Any, List
from errors import ConfigError
from github.Team import Team
from github.Organization import Organization

log = logging.getLogger()


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
            self.config = yaml.safe_load(file_stream)

        # Logging setup
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s [%(levelname)s] %(message)s'
        )

        log_level = self._get_config_item(["logging", "level"], "INFO")
        log.setLevel(log_level)

        file_logging_enabled = self._get_config_item(
            ["logging", "file_logging"], "enabled", False
        )
        if file_logging_enabled:
            file_logging_filepath = self._get_config_item(
                ["logging", "file_logging", "filepath"], "bot.log"
            )
            handler = logging.FileHandler(file_logging_filepath)
            handler.setFormatter(formatter)
            log.addHandler(handler)

        console_logging_enabled = self._get_config_item(
            ["logging", "console_logging", "enabled"], True
        )
        if console_logging_enabled:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            log.addHandler(handler)

        # Github setup
        self.github_user = None  # Set later once we connect to github successfully

        self.github_access_token = self._get_config_item(
            ["github", "access_token"]
        )

        self.github_repo = self._get_config_item(["github", "repo"])

        # Github labels
        self.github_proposal_label = self._get_config_item(
            ["github", "labels", "proposal"]
        )
        self.github_fcp_label = self._get_config_item(
            ["github", "labels", "fcp"]
        )
        self.github_fcp_proposed_label = self._get_config_item(
            ["github", "labels", "fcp_proposed"]
        )
        self.github_disposition_merge_label = self._get_config_item(
            ["github", "labels", "disposition_merge"]
        )
        self.github_disposition_close_label = self._get_config_item(
            ["github", "labels", "disposition_close"]
        )
        self.github_disposition_postpone_label = self._get_config_item(
            ["github", "labels", "disposition_postpone"]
        )

        self.github_fcp_proposal_template_path = self._get_config_item(
            ["github", "fcp_proposal_template_path"]
        )

        self.github_org_name = self._get_config_item(["github", "org"])
        self.github_team_name = self._get_config_item(["github", "team"])

        # FCP information
        self.fcp_time_days = self._get_config_item(["fcp", "time_days"], required=False)
        self.fcp_timer_json_filepath = self._get_config_item(
            ["fcp", "timer_json_filepath"]
        )

        # Webhook setup
        self.webhook_host = self._get_config_item(["webhook", "host"], "0.0.0.0")
        self.webhook_port = self._get_config_item(["webhook", "port"], 5050)
        self.webhook_path = self._get_config_item(["webhook", "path"], "/webhook")
        self.webhook_secret = self._get_config_item(["webhook", "secret"], required=False)

    def _get_config_item(
            self,
            path: List[str],
            default: Any = None,
            required: bool = True,
    ) -> Any:
        """Get a config option from a path and option name, specifying whether it is
        required.

        Raises:
            ConfigError: If required is specified and the object is not found
                (and there is no default value provided), this error will be raised
        """
        option_name = path.pop(-1)

        path_str = '.'.join(path)

        # Sift through the config dicts specified by `path` to get the one containing
        # our option
        config_dict = self.config
        for name in path:
            config_dict = config_dict.get(name)
            if not config_dict:
                if required:
                    raise ConfigError(f"Config option {path_str} is required")
                else:
                    config_dict = {}

        # Retrieve the option
        option = config_dict.get(option_name, default)
        if required and not option:
            raise ConfigError(f"Config option {path_str+'.'+option_name} is required")

        return option


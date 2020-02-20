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

from github import Github
from github.GithubException import UnknownObjectException
import logging

from config import Config
from webhook import WebhookHandler

log = logging.getLogger(__name__)


def main():
    # Read the config file
    config = Config("config.yaml")

    # Log into github with provided access token
    github = Github(config.github_access_token)
    if not github:
        log.fatal("Unable to connect to github")
        return

    # Connect to the configured repository
    repo = github.get_repo(config.github_repo)
    if not repo:
        log.fatal(f"Unable to connect to github repo '{config.github_repo}'")
        return

    # Get the user object of the bot
    config.github_user = github.get_user()
    if not config.github_user:
        log.fatal("Unable to download our own github user information")
        return

    # Get the proposal team object
    try:
        config.github_org = github.get_organization(config.github_org_name)
    except UnknownObjectException:
        log.fatal(f"Unable to find Github org '{config.github_org_name}'")
        return

    try:
        config.github_team = config.github_org.get_team_by_slug(config.github_team_name)
    except UnknownObjectException:
        log.fatal(f"Unable to find or access Github team '{config.github_team_name}'. "
                  f"Make sure your bot is part of the team and has the read:org "
                  f"permission")
        return

    # Create a webhook handler
    webhook_handler = WebhookHandler(config, github, repo)

    # Start accepting webhooks
    webhook_handler.run()


if __name__ == "__main__":
    main()

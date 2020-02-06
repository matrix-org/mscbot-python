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

# Download all the issues/prs with [proposal] tag

# Figure out their current state

# Find the MSCBot comments of the relevant ones

# Figure out their current MSCBot state

# ---

# Webhook API to update state of things

# Post comments when necessary
from github import Github
from github_scraper import GithubScraper
import logging

from config import Config
from storage import Storage
from webhook import WebhookHandler

log = logging.getLogger(__name__)


def main():
    # Read the config file
    config = Config("config.yaml")

    # Configure the database
    #store = Storage(config.database_filepath)
    store = None

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
    config.github_org = github.get_organization(config.github_org_name)
    if not config.github_org:
        log.fatal(f"Unable to find Github org '{config.github_org_name}'")
    config.github_team = config.github_org.get_team(config.github_team_name)
    if not config.github_team:
        log.fatal(f"Unable to find Github team '{config.github_team_name}'")

    # Scrape all the current information off github
    scraper = GithubScraper(config, store, github, repo)
    #scraper.scrape()

    # Create a webhook handler
    webhook_handler = WebhookHandler(store, config, github, repo)

    # Start accepting webhooks
    webhook_handler.run()


if __name__ == "__main__":
    main()

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

log = logging.getLogger(__name__)


def main():
    # Read the config file
    config = Config("config.yaml")

    # Configure the database
    store = Storage(config.database_filepath)

    # Log into github with provided access token
    github = Github(config.github_access_token)
    if not github:
        log.fatal("Unable to connect to github")
        return

    repo = github.get_repo(config.github_repo)
    if not repo:
        log.fatal(f"Unable to connect to github repo {config.github_repo}")
        return

    # Scrape all the current information off github
    scraper = GithubScraper(config, store, github, repo)
    scraper.scrape()



    # Create a webhook handler
    # Separate script to scrape before the initial run?
    # Could run if database isn't populated yet?


if __name__ == "__main__":
    main()

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

import psycopg2

latest_db_version = 0

log = logging.getLogger(__name__)


class Storage(object):
    def __init__(self, db_path):
        """Setup the database
        Runs an initial setup or migrations depending on whether a database file has already
        been created

        Args:
            db_path (str): Path to the database (postgres)
        """
        self.db_path = db_path

        # Connect to the database
        self.conn = psycopg2.connect(db_path)
        self.cur = self.conn.cursor()

        try:
            self.cur.execute("SELECT current FROM migrations")

            row = self.cur.fetchone()
            if not row:
                self._initial_setup()

            # TODO: Migrations
        except Exception:
            # migrations table doesn't exist yet, this is a new database
            self.conn.rollback()
            self._initial_setup()

    def _initial_setup(self):
        """Initial setup of the database"""
        log.info("Performing initial database setup...")

        # Migrations table #

        # Holds information about database migrations
        self.cur.execute(
            """
            CREATE TABLE migrations (
                current INTEGER PRIMARY KEY
            )
        """
        )

        # Initial migration version
        self.cur.execute(
            """
            INSERT INTO migrations
            (current)
            VALUES (0)
        """
        )

        # FCP timers table #

        self.cur.execute(
            """
            CREATE TABLE fcp_timers (
                proposal_num INTEGER PRIMARY KEY,
                end_timestamp INTEGER NOT NULL
            )
        """
        )

        self.cur.execute(
            """
            CREATE UNIQUE INDEX fcp_timers_proposal_num ON fcp_timers (proposal_num)
        """
        )

        log.info("Database setup complete")

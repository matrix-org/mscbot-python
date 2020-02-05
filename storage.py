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
import psycopg2
import logging

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

        # Check if we need to perform a migration
        try:
            self.cur.execute("SELECT current FROM migrations")

            row = self.cur.fetchone()
            if not row:
                self._initial_setup()
            else:
                current_migration = row[0]
                self._run_migrations(current_migration)
        except Exception:
            # migrations table doesn't exist yet, this is a new database
            self.conn.rollback()
            self._initial_setup()

    def _initial_setup(self):
        """Initial setup of the database"""
        log.info("Performing initial database setup...")

        # Migrations table #

        # Holds information about database migrations
        self.cur.execute("""
            CREATE TABLE migrations (
                current INTEGER PRIMARY KEY
            )
        """)

        # Initial migration version
        self.cur.execute("""
            INSERT INTO migrations
            (current)
            VALUES (0)
        """)

        # Proposal table #

        self.cur.execute("""
            CREATE TABLE proposal (
                num INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                shepherd TEXT,
                labels TEXT[] NOT NULL
            )
        """)

        self.cur.execute("""
            ALTER TABLE proposal ADD CONSTRAINT proposal_num UNIQUE (numj
        """)

        # Bot comment table #

        # Comments made by the bot
        self.cur.execute("""
            CREATE TABLE bot_comment (
                id INTEGER PRIMARY KEY,
                proposal_num TEXT NOT NULL
            )
        """)

        self.cur.execute("""
            CREATE UNIQUE INDEX bot_comment_id ON bot_comment (id)
        """)

        # Team table #

        # Teams that are in charge of various parts of the spec
        self.cur.execute("""
            CREATE TABLE team (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        self.cur.execute("""
            CREATE UNIQUE INDEX team_id ON team (id)
        """)
        self.cur.execute("""
            CREATE UNIQUE INDEX team_name ON team (name)
        """)

        # Teammates table #

        # Members in each team
        self.cur.execute("""
            CREATE TABLE teammates (
                team_id INTEGER NOT NULL,
                name TEXT NOT NULL
            )
        """)
        self.cur.execute("""
            CREATE UNIQUE INDEX team_team_id_name ON teammates (team_id, name)
        """)

        self.conn.commit()

        log.info("Database setup complete")

    def _run_migrations(self, current_migration: int):
        pass

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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.job import Job
from storage import Storage
from datetime import datetime
from errors import ProposalNotInFCP

log = logging.getLogger(__name__)


class FCPTimers(object):
    """An object to store FCP timer information. Timers are stored in a database

    Args:
        callback_func: Callback function. Will be called with the proposal_num (int)
            as an argument
    """

    def __init__(self, store: Storage, callback_func):
        self.store = store
        self.callback_func = callback_func

        # Create a BackgroundScheduler.
        # This will fire events when FCPs complete
        # When an event is scheduled, a Job is returned
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # Create a dict from proposal number to scheduler Job
        self.timers = {}

        # Load timer information
        self._db_load_timers()

    def new_timer(self, run_time: datetime, proposal_num: int, save=True):
        """Start a new timer. Saves the timer to the db if `save` is True"""
        # Schedule a new job
        job = self.scheduler.add_job(self._run_callback, DateTrigger(run_time),
                                     args=[proposal_num])

        # Record the timer's job ID along with the proposal number
        self.timers[proposal_num] = job

        # Save timer to db
        if save:
            self._db_save_timer(run_time, proposal_num)

    def cancel_timer_for_proposal_num(self, proposal_num: int):
        """Stop a scheduled timer and delete it from disk"""
        # Grab the Job for this proposal
        if proposal_num not in self.timers:
            raise ProposalNotInFCP("This proposal does not have an FCP timer")

        # Cancel this job if hasn't already been
        job = self.timers[proposal_num]  # type: Job
        if self.scheduler.get_job(job.id):
            job.remove()

        self.timers.pop(proposal_num)

        # Remove it from the db
        self._db_delete_timer(proposal_num)

    def _db_load_timers(self):
        """Load all known FCP timers from the DB into self.timers"""
        with self.store.conn:
            self.store.cur.execute("SELECT * FROM fcp_timers")
            rows = self.store.cur.fetchall()
            if not rows:
                return

            for row in rows:
                proposal_num = row[0]
                timestamp = row[1]

                run_time = datetime.fromtimestamp(timestamp)
                self.new_timer(run_time, proposal_num, save=False)

    def _db_save_timer(self, timestamp: datetime, proposal_num: int):
        """Saves a timer to the database"""
        with self.store.conn:
            self.store.cur.execute("""
            INSERT INTO fcp_timers (proposal_num, end_timestamp)
                VALUES (%s, %s)
            ON CONFLICT (proposal_num)
            DO UPDATE
                SET end_timestamp = %s
                WHERE fcp_timers.proposal_num = %s
            """, (
                proposal_num, timestamp.timestamp(),
                proposal_num, timestamp.timestamp(),
            ))

    def _db_delete_timer(self, proposal_num: int):
        """Deletes a timer from the database"""
        with self.store.conn:
            log.info("DELETING %s", proposal_num)
            self.store.cur.execute(
                "DELETE FROM fcp_timers WHERE proposal_num = %s",
                (proposal_num,)
            )

    def _run_callback(self, proposal_num: int):
        """Fires when a timer goes off. Delete the timer and call the callback function"""
        self.cancel_timer_for_proposal_num(proposal_num)
        self.callback_func(proposal_num)

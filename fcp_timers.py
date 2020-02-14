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
import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime
from errors import ProposalNotInFCP

log = logging.getLogger(__name__)


class FCPTimers(object):
    """An object to store FCP timer information. Timers are stored in a json
    file along with the corresponding proposal number.

    Example:

        {
            "123": "1581592213",  # proposal #123 FCP ends at this unix timestamp
            "456": "1581592416"
        }

    Args:
        filepath: path to the timer json file
        callback_func: Callback function. Will be called with the proposal_num (int)
            as an argument
    """

    def __init__(self, filepath: str, callback_func):
        self.filepath = filepath
        self.callback_func = callback_func

        # Create a BackgroundScheduler.
        # This will fire events when FCPs complete
        # When an event is scheduled, a Job is returned
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # Load timer information

        # Create a dict from proposal number to scheduler Job
        self.timers = {}
        try:
            with open(filepath) as data_file:
                timer_dict = json.loads(data_file.read())
                for proposal_num, timestamp in timer_dict.items():
                    # Convert the timestamp to a datetime
                    run_time = datetime.fromtimestamp(timestamp)

                    self.new_timer(run_time, proposal_num)
        except FileNotFoundError:
            # The file doesn't exist yet
            log.debug(
                "File at fcp.timer_json_filepath does not exist yet. Creating "
                "one..."
            )
            with open(filepath, 'w+') as data_file:
                data_file.write("{}")

    def new_timer(self, run_time: datetime, proposal_num: int):
        """Start a new timer. Saves the timer to disk"""
        # Schedule a new job
        job = self.scheduler.add_job(self._run_callback, DateTrigger(run_time),
                                     args=[proposal_num])

        # Record the timer's job ID along with the proposal number
        self.timers[proposal_num] = job

        # Save timers
        self._save_timers_to_disk()

    def cancel_timer_for_proposal_num(self, proposal_num: int):
        """Stop a scheduled timer and delete it from disk"""
        # Grab the Job for this proposal
        if proposal_num not in self.timers:
            raise ProposalNotInFCP("This proposal does not have an FCP timer")

        # Cancel this job if hasn't already been
        job = self.timers[proposal_num]  # type: Job
        if self.scheduler.get_job(job.id):
            job.remove()

        # Remove it from disk
        self.timers.pop(proposal_num)
        self._save_timers_to_disk()

    def _save_timers_to_disk(self):
        """Takes the current state of self.timers and overwrites the contents on disk"""
        # Construct a dict of proposal_num: unix timestamp
        proposal_num_to_timestamp = {}
        for proposal_num, job in self.timers.items():
            proposal_num_to_timestamp[proposal_num] = int(job.next_run_time.timestamp())

        # Write that dict to disk
        with open(self.filepath, 'w+') as data_file:
            data_file.write(json.dumps(proposal_num_to_timestamp))

    def _run_callback(self, proposal_num: int):
        """Fires when a timer goes off. Delete the timer and call the callback function"""
        self.cancel_timer_for_proposal_num(proposal_num)
        self.callback_func(proposal_num)

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


class ConfigError(RuntimeError):
    """An error encountered during reading the config file
    Args:
        msg (str): The message displayed on error
    """

    def __init__(self, msg):
        super(ConfigError, self).__init__("%s" % (msg,))


class ProposalNotInFCP(RuntimeError):
    """An error encountered when a command is performed on an FCP that could
    only be performed on one in FCP, but it is not in FCP

    Args:
        msg (str): The message displayed on error
    """

    def __init__(self, msg):
        super(ProposalNotInFCP, self).__init__("%s" % (msg,))

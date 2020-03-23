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

from setuptools import setup


setup(
    name="mscbot",
    version="0.0.1",
    py_modules=["mscbot"],
    description="A bot to help manage the MSC process",
    install_requires=[
        "PyGithub>=1.45",
        "PyYAML>=5.3",
        "github-webhook>=1.0.3",
        "waitress>=1.4.3",
        "jinja2>=2.11.1",
        "APScheduler>=3.6.3",
        "psycopg2-binary>=2.8.4",
    ],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
    ],
)

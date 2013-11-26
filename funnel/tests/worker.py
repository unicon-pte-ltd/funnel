# -*- coding: utf-8 -*-
#
# Copyright 2013 Unicon Pte. Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, with_statement

from funnel.queue import Manager
from funnel.testing import AsyncWorkerTestCase
from funnel.worker import Worker

class WorkerTestCase(AsyncWorkerTestCase):
    def get_publisher(self):
        return Manager()

    def get_worker(self):
        def echo(worker, body):
            if "error_occurred" in body:
                raise Exception("Error occurred")
            return body

        return Worker(
            handlers = {"echo": echo},
            queue    = Manager(),
        )

    def test_delivered(self):
        response = self.publish(
            {
                "task": "echo",
                "a": 1,
                "b": 2,
                "c": 3,
            },
        )

        self.assertEqual(
            response,
            {
                "task": "echo",
                "a": 1,
                "b": 2,
                "c": 3,
            }
        )

    def test_raise_exception_in_task(self):
        response = self.publish(
            {
                "task": "echo",
                "error_occurred": True,
            },
        )

        self.assertTrue(response["error"])

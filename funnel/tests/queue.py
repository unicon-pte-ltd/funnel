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
from time import time
from tornado.testing import AsyncTestCase
from tornado.ioloop import IOLoop

class TestManager(AsyncTestCase):
    def get_new_ioloop(self):
        return IOLoop.instance()

    def test_basis(self):
        queue = Manager()
        self.addCleanup(queue.close_connection)
        queue.connect()

        counter = {"n": 0}
        def on_message(body):
            self.assertEqual(body, {"message": "Hello, world!"})
            counter["n"] += 1

        queue.start_consuming(
            on_message,
        )

        queue.publish({"message": "Hello, world!"}, routing_key=queue.name)

        IOLoop.instance().add_timeout(time() + 0.2, self.stop)
        self.wait()

        self.assertEqual(counter["n"], 1)

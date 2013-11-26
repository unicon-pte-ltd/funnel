# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, with_statement

from funnel.queue import Manager
from funnel.testing import AsyncWorkerTestCase
from funnel.worker import Worker

class FelloWorkerTestCase(AsyncWorkerTestCase):
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

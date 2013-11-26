# -*- coding: utf-8 -*-

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

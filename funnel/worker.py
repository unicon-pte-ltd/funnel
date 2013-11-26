# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, with_statement

class Worker(object):
    def __init__(self, handlers, queue):
        self._handlers = handlers
        self._queue    = queue

    def destruct(self):
        self._queue.close_connection()

    def _on_message(self, body):
        handler = self._handlers.get(body["task"])
        if handler:
            return handler(self, body)
        else:
            pass # TODO error handling

    def start(self, **kwargs):
        self._queue.connect()
        self._queue.start_consuming(self._on_message, **kwargs)

    def get_queue_name(self):
        return self._queue.name

    queue_name = property(get_queue_name)

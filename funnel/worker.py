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

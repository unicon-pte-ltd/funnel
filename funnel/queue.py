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

import json
import logging
from pika import BasicProperties, ConnectionParameters, BlockingConnection
from pika.adapters.tornado_connection import TornadoConnection
from pika.exceptions import AMQPConnectionError
from time import time, sleep
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from tornado.stack_context import ExceptionStackContext
from uuid import uuid4

CONNECTION_RETRY_INTERVAL = 1.0

class Message(object):
    def __init__(self, queue, callback, no_ack=False, rpc=False):
        self._queue      = queue
        self._callback   = callback
        self._no_ack     = no_ack
        self._rpc        = rpc
        self._start_time = time()

    def _stack_context_handle_exception(self, type, value, traceback):
        logging.error("Uncaught exception\n%r", self._body, exc_info=(type, value, traceback))
        return True

    def process(self, unused_channel, basic_deliver, properties, body):
        self._queue._increment_working_count()
        self._unused_channel = unused_channel
        self._basic_deliver  = basic_deliver
        self._properties     = properties
        self._body           = json.loads(body)

        with ExceptionStackContext(self._stack_context_handle_exception):
            try:
                result = self._callback(self._body)
            except Exception as e:
                if not self._no_ack:
                    self.acknowledge()
                self.finish({"error": True})
                raise

            if isinstance(result, Future):
                def future_complete(f):
                    if not self._no_ack:
                        self.acknowledge()

                    try:
                        self.finish(f.result())
                    except Exception as e:
                        self.finish({"error": True})
                        raise

                    self._queue._decrement_working_count()
                IOLoop.current().add_future(result, future_complete)
                return

            if not self._no_ack:
                self.acknowledge()

            self.finish(result)
            self._queue._decrement_working_count()

    def process_time(self):
        return time() - self._start_time

    def _log(self):
        logging.info("%r %.2fms", self._body, 1000.0 * self.process_time())

    def acknowledge(self):
        self._queue._channel.basic_ack(self._basic_deliver.delivery_tag)

    def finish(self, result):
        if self._rpc:
            self._queue.publish(
                result,
                correlation_id = self._properties.correlation_id,
                routing_key    = self._properties.reply_to
            )

        self._log()

class BaseManager(object):
    def __init__(self, queue="", exchange="", routing_key="", exclusive=False, persistent=False):
        self._dynamic_queue        = False if queue else True
        self._connection           = None
        self._channel              = None
        self._exchange             = exchange
        self._queue                = queue
        self._routing_key          = routing_key
        self._exclusive            = exclusive
        self._ready                = False
        self._persistent          = persistent

    def get_name(self):
        return self._queue

    name = property(get_name)

    def publish(self, message, correlation_id=None, reply_to=None, routing_key=None, serializer=None):
        if routing_key is None:
            routing_key = self._routing_key

        if not self._ready: # TODO Flushing stacked messages
            self._on_queue_not_ready(message, routing_key)

        properties = {
            "content_type"   : "application/json",
            "correlation_id" : correlation_id,
            "reply_to"       : reply_to,
        }

        if self._persistent:
            properties['delivery_mode'] = 2

        self._channel.basic_publish(
            exchange    = self._exchange,
            routing_key = routing_key,
            body        = json.dumps(message, default=serializer),
            properties  = BasicProperties(**properties),
        )

    def _on_queue_not_ready(self, message, routing):
        logging.error("Failer to publish to %s: %r", routing, message)


class SyncManager(BaseManager):
    def connect(self, **kwargs):
        try:
            self._connection = BlockingConnection(
                ConnectionParameters(**kwargs),
            )
            self._channel = self._connection.channel()
            self._channel.queue_declare(
                queue     = "" if self._dynamic_queue else self._queue,
                exclusive = self._exclusive,
                durable = self._persistent
            )
        except AMQPConnectionError as e:
            logging.exception(e)
            self.reconnect(**kwargs)

    def reconnect(self, **kwargs):
        sleep(CONNECTION_RETRY_INTERVAL)
        self.connect(**kwargs)

    def close_connection(self):
        self._connection.close()


class AsyncManager(BaseManager):

    _process_count = 0
    _working_count = 0
    _last_finish_time = 0

    def __init__(self, queue="", exchange="", routing_key="", exclusive=False, ioloop=None, stop_ioloop_on_close=False, stop_on_max_processed=False, max_process_count=1):
        if ioloop is None:
            ioloop = IOLoop.current()

        self._ioloop               = ioloop
        self._stop_ioloop_on_close = stop_ioloop_on_close
        self._stop_on_max_processed = stop_on_max_processed
        self._max_process_count = max_process_count

        super(Manager, self).__init__(queue, exchange, routing_key, exclusive=False)

    def _increment_working_count(self):
        self._process_count += 1
        self._working_count += 1

    def _decrement_working_count(self):
        self._working_count -= 1
        self._last_finish_time = time()

    def _connect(self, async=True, **kwargs):
        def callback():
            try:
                self._connection = TornadoConnection(
                    ConnectionParameters(**kwargs),
                    on_open_callback     = self._on_connection_open(async, **kwargs),
                    stop_ioloop_on_close = self._stop_ioloop_on_close,
                    custom_ioloop        = self._ioloop,
                )
            except AMQPConnectionError as e:
                logging.exception(e)
                self.reconnect(async, **kwargs)
        return callback

    def _stack_context_handle_exception(self, type, value, traceback):
        logging.error("Uncaught exception", exc_info=(type, value, traceback))
        return True

    # 1秒はackが到達するであろう時間
    def _check_max_processed(self):
        logging.info("_check_max_processed")
        if self._stop_on_max_processed and self._process_count >= self._max_process_count and self._working_count == 0 and time() - self._last_finish_time > 1:
            logging.info("edn ioloop by max_processed")
            self._ioloop.stop()
        else:
            self._ioloop.add_timeout(
                time() + 10, self._check_max_processed
            )

    def connect(self, **kwargs):
        kwargs.update({'async': False})
        with ExceptionStackContext(self._stack_context_handle_exception):
            self._connect(**kwargs)()

        if self._stop_ioloop_on_close:
            self._ioloop.add_timeout(
                time() + 10, self._check_max_processed
            )

        self._ioloop.start()

    def reconnect(self, async=True, **kwargs):
        self._ioloop.add_timeout(time() + CONNECTION_RETRY_INTERVAL, self._connect(async, **kwargs))

    def _on_connection_open(self, async=True, **kwargs):
        def callback(connection):
            connection.add_on_close_callback(self._on_connection_closed(**kwargs))
            connection.channel(on_open_callback=self._on_channel_open(async))
        return callback

    def _on_connection_closed(self, **kwargs):
        def callback(connection, reply_code, reply_text):
            self._ready   = False
            self._channel = None
            self.reconnect(**kwargs)
        return callback

    def _on_channel_open(self, async=True):
        def callback(channel):
            self._channel = channel
            self._channel.queue_declare(
                callback  = self._on_queue_declareok(async),
                queue     = "" if self._dynamic_queue else self._queue,
                exclusive = self._exclusive,
                durable = self._persistent,
            )
        return callback

    def _on_queue_declareok(self, async=True):
        def callback(result):
            self._queue = result.method.queue
            self._ready = True
            if not async:
                self._ioloop.stop()
        return callback

    def _on_message(self, callback, no_ack=False, rpc=False):
        def wrapper(*args, **kwargs):
            message = Message(self, callback, no_ack, rpc)
            message.process(*args, **kwargs)
        return wrapper

    def call(self, message, **kwargs):
        self.publish(
            message,
            correlation_id = str(uuid4()),
            reply_to       = self._queue,
            **kwargs
        )

    def start_consuming(self, callback, no_ack=False, rpc=False):
        self._channel.basic_consume(
            self._on_message(callback, no_ack, rpc),
            queue  = self._queue,
            no_ack = no_ack,
        )

    def close_connection(self): # TODO synchronous disconnecting
        self._connection.callbacks.clear()
        self._connection.close()


# alias
Manager = AsyncManager

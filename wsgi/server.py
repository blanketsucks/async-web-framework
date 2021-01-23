
from .httpparser import HTTPParserMixin
from .request import Request

import asyncio
from asyncio import transports
from typing import Optional
from httptools import HttpRequestParser

class Server(asyncio.Protocol, HTTPParserMixin):
    def __init__(self, loop: asyncio.AbstractEventLoop, *, app, handler) -> None:
        
        self._loop = loop
        self._url = None

        self._headers = {}
        self._body = None

        self._transport = None
        self._request_parser = HttpRequestParser(self)

        self._request = None
        self._request_cls = Request

        self._request_handler = handler
        self._request_handler_task = None

        self._encoding = 'utf-8'
        self._app = app

        self._status = 200

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._loop.create_task(self._app.dispatch('on_connection_made', transport))
        self._transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self._transport = None
        self._loop.create_task(self._app.dispatch('on_connection_lost', exc))

    def response_writer(self, response):
        self._transport.write(str(response).encode(self._encoding))
        self._transport.close()

    def data_received(self, data: bytes) -> None:
        self._request_parser.feed_data(data)
        self._loop.create_task(self._app.dispatch('on_socket_receive', data))

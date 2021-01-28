

from .httpparser import HTTPParserMixin
from .request import Request
from .response import Response

import asyncio
from asyncio import transports
import typing
from httptools import HttpRequestParser

if typing.TYPE_CHECKING:
    from .app import Application

class Server(asyncio.Protocol, HTTPParserMixin):
    def __init__(self, loop: asyncio.AbstractEventLoop, *, app: 'Application', handler: typing.Coroutine) -> None:
        
        self._loop = loop
        self._url: str = None

        self._headers: typing.Dict = {}
        self._body = None

        self._transport = None
        self._request_parser = HttpRequestParser(self)

        self._request: Request = None
        self._request_cls = Request

        self._request_handler = handler
        self._request_handler_task: asyncio.Task = None

        self._encoding: str = 'utf-8'
        self._app = app

        self._status: int = 200

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._loop.create_task(self._app.dispatch('on_connection_made', transport))
        self._transport = transport

    def connection_lost(self, exc: typing.Optional[Exception]) -> None:
        self._transport = None
        self._loop.create_task(self._app.dispatch('on_connection_lost', exc))

    def response_writer(self, response: Response):
        self._transport.write(str(response).encode(self._encoding))
        self._transport.close()

    def data_received(self, data: bytes) -> None:
        self._request_parser.feed_data(data)
        self._loop.create_task(self._app.dispatch('on_socket_receive', data))

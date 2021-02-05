

from .request import Request
from .response import Response

import asyncio
from asyncio import transports
import typing
from httptools import HttpRequestParser

if typing.TYPE_CHECKING:
    from .app import Application


class Server(asyncio.Protocol):
    __slots__ = (
        'loop', 'headers', 'request_class', 'parser', 'handler',
        'encoding', 'app', 'status', 'url', 'handler_task',
        'request', 'body', 'transport', 'connection_type', 'host',
        'http_version', 'method', 'path', 'user_agent'
    )

    def __init__(self, loop: asyncio.AbstractEventLoop, *, app: 'Application', handler: typing.Coroutine) -> None:
        
        self.loop = loop
        self.headers: typing.Dict = {}
        self.request_class = Request
        self.parser = HttpRequestParser(self)
        self.handler = handler
        self.encoding: str = 'utf-8'
        self.app = app
        self.status: int = 200

        self.url: str = None
        self.handler_task: asyncio.Task = None
        self.request: Request = None
        self.body = None
        self.transport = None
        self.connection_type = None
        self.host = None
        self.http_version = None
        self.method = None
        self.path = None
        self.user_agent = None

    def on_body(self, body):
        self.body = body

    def on_header(self, header, value):
        header = header.decode(self.encoding)
        self.headers[header] = value.decode(self.encoding)

    def on_status(self, status):
        status = status.decode(self.encoding)
        self.status = status

    def on_headers_complete(self):
        self.request = self.request_class(
            version=self.http_version,
            method=self.method,
            url=self.path,
            headers=self.headers,
            body=self.body,
            transport=self.transport,
            status_code=self.status
        )

    def on_message_complete(self):
        self.handler_task = self.loop.create_task(
            self.handler(self.request, self.response_writer)
        )
        self.loop.create_task(
            self.app.dispatch('on_request', self.request)
        )

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self.loop.create_task(self.app.dispatch('on_connection_made', transport))
        self.transport = transport

    def connection_lost(self, exc: typing.Optional[Exception]) -> None:
        self.transport = None
        self.loop.create_task(self.app.dispatch('on_connection_lost', exc))

    def response_writer(self, response: Response):
        self.transport.write(str(response).encode(self.encoding))
        self.transport.close()

    def data_received(self, data: bytes) -> None:
        message = data.decode('utf-8')
        strings = message.split('\n')

        self.get_http_info(strings)
        self.parser.feed_data(data)

        self.loop.create_task(self.app.dispatch('on_socket_receive', data))

    def get_http_info(self, data: list):
        method, path, http_version = data[0].split(' ')

        self.method = method
        self.path = path
        self.http_version = http_version


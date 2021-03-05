import datetime
from .request import Request
from .server import http, HTTPProtocol, HTTPConnection
from .response import Response

import typing
import asyncio

if typing.TYPE_CHECKING:
    from .app import Application

__all__ = (
    'ApplicationProtocol',
    'run_server'
)

class ApplicationProtocol(HTTPProtocol):
    def __init__(self, app: 'Application',*, loop: typing.Optional[asyncio.AbstractEventLoop]) -> None:
        self.loop = loop
        self.app = app

        self.handler = app._request_handler
        self.request: Request = None

    async def response_writer(self, response: Response):
        await self.conn.write(
            status=response.status,
            body=response.body,
            content_type=response.content_type,
            headers=response.headers
        )
        self.conn.close()

    async def on_request(self):
        self.request = Request(
            method=self.method,
            url=self.path,
            status_code=200,
            headers=self.http_info,
            protocol=self,
            date=datetime.datetime.utcnow(),
            version='1.1'
        )
        await self.handler(self.request, self.response_writer)

    async def on_connection_made(self, connection: HTTPConnection):
        self.conn = connection

    async def on_socket_receive(self, data: bytes):
        self.parse_data(data)

    async def on_error(self, exc: Exception):
        raise exc

async def run_server(protocol: ApplicationProtocol,
                    app: 'Application',
                    host: str=...,
                    *,
                    port: int=...,
                    loop: asyncio.AbstractEventLoop=...):

    if not isinstance(protocol, ApplicationProtocol):
        fmt = 'Expected ApplicationProtocol but got {0.__class__.__name__} instead'.format(protocol)
        raise ValueError(fmt)

    host = '127.0.0.1' if host is Ellipsis else host
    port = 8080 if port is Ellipsis else host
    loop = asyncio.get_event_loop() if loop is Ellipsis else loop

    server = http.HTTPServer(
        protocol=protocol,
        host=host,
        port=port,
        loop=loop
    )

    app._server = server
    await server.serve()

    


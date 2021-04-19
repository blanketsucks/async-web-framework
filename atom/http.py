
from atom.sockets.server import WebsocketServer
from .request import Request
from .response import Response
from .sockets import (
    WebsocketConnection,
    WebsocketTransport,
    Request as ClientRequest,
    WebsocketProtocol
)

import datetime
import typing
import asyncio

if typing.TYPE_CHECKING:
    from .app import Application

__all__ = (
    'ApplicationProtocol',
    'run_server'
)


class ApplicationProtocol(WebsocketProtocol):
    def __init__(self, app: 'Application', *, loop: typing.Optional[asyncio.AbstractEventLoop]) -> None:
        self.loop = loop
        self.app = app

        self.handler = app._request_handler
        self._request: Request = None

    async def response_writer(self, response: Response):
        await self.transport.send(response.encode())
        self.transport.close()

    async def on_request(self, method: str, path: str, body: str, headers: typing.Mapping[str, str]):
        self._request = Request(
            method=method,
            url=path,
            body=body,
            headers=headers,
            protocol=self,
            date=datetime.datetime.utcnow(),
            version='1.1'
        )
        
        await self.handler(self._request, self.response_writer, ws=self._ws)

    async def on_connection_made(self, transport: WebsocketTransport):
        self.transport = transport
        self._ws = WebsocketConnection(transport)

    async def on_connection_lost(self):
        return

    async def on_data_receive(self, data: bytes):
        await self.app.dispatch('on_data_receive', data)

        request = ClientRequest.parse(data)
        await self.on_request(
            method=request.method,
            path=request.path,
            body=request.body,
            headers=request.headers
        )



async def run_server(protocol: ApplicationProtocol,
                     app: 'Application',
                     host: str = ...,
                     *,
                     port: int = ...,
                     loop: asyncio.AbstractEventLoop = ...):
    if not isinstance(protocol, ApplicationProtocol):
        fmt = 'Expected ApplicationProtocol but got {0.__class__.__name__} instead'.format(protocol)
        raise ValueError(fmt)

    host = '127.0.0.1' if host is ... else host
    port = 8080 if port is ... else port
    loop = asyncio.get_event_loop() if loop is ... else loop
    
    server = WebsocketServer(
        protocol=protocol,
        host=host,
        port=port,
        backlog=app._backlog
    )

    app._server = server
    await server.serve()

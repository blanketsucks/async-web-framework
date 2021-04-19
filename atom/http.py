
from atom.sockets.server import WebsocketServer
from .request import Request
from .response import Response
from .sockets import (
    Transport,
    WebsocketTransport,
    Request as ClientRequest,
    WebSocketOpcode,
    Server,
    Websocket,
    WebSocketCloseCode,
    WebsocketProtocol
)

import datetime
import typing
import asyncio
import socket

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

class WebsocketConnection:
    def __init__(self, socket: Websocket) -> None:
        self._socket = socket

    @property
    def laddr(self):
        return self._socket.laddr

    @property
    def raddr(self):
        return self._socket.raddr

    async def handshake(self):
        await self._socket.handshake()

    async def ping(self, data: bytes=...):
        await self._socket.ping(data)

    async def pong(self, data: bytes=...):
        await self._socket.pong(data)

    async def binary(self, data: bytes=...):
        await self._socket.send_binary(data)

    async def continuation(self, data: bytes=...):
        await self._socket.continuation(data)

    async def send_bytes(self, data: bytes=..., *, opcode: WebSocketOpcode=...):
        await self._socket.send_bytes(data, opcode)

    async def send_str(self, data: str=..., *, opcode: WebSocketOpcode=...):
        await self._socket.send_str(data, opcode)

    async def send_json(self, data: typing.Dict[str, typing.Any]=..., *, opcode: WebSocketOpcode=...):
        await self._socket.send_json(data, opcode)

    async def receive(self):
        data = await self._socket.receive()
        return data

    async def receive_bytes(self):
        data = await self._socket.receive_bytes()
        return data

    async def receive_str(self):
        data = await self._socket.receive_str()
        return data

    async def receive_json(self):
        data = await self._socket.receive_json()
        return data

    async def close(self, data: bytes=..., code: WebSocketCloseCode=...):
        await self._socket.close(code=code, data=data)

    def shutdown(self):
        self._socket._close()
        self._socket.shutdown(socket.SHUT_RDWR)
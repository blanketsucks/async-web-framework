from .bases import Protocol
from .connection import HTTPConnection
from .sockets import WebSocketFrame

import typing
import asyncio

__all__ = (
    'HTTPProtocol',
)


class HTTPProtocol(Protocol):
    def __init__(self, loop: typing.Optional[asyncio.AbstractEventLoop]) -> None:
        self.loop = loop

    async def on_connection_made(self, connection: HTTPConnection):
        ...

    async def on_request(self, body: str, headers: typing.Mapping[str, str]):
        ...


    def __repr__(self) -> str:
        return '<HTTPProtcol>'

class WebsocketProtocol(Protocol):
    def __init__(self, loop: typing.Optional[asyncio.AbstractEventLoop]) -> None:
        self.loop = loop

    async def on_websocket_close(self):
        ...

    async def on_websocket_handshake(self, data: bytes):
        ...

    async def on_websocket_frame(self, frame: WebSocketFrame):
        ...

    async def on_websocket_binary(self, data: bytes):
        ...

    async def on_websocket_text(self, data: bytes):
        ...

    async def on_websocket_ping(self, data: bytes):
        ...

    async def on_websocket_pong(self, data: bytes):
        ...
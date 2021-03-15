from .bases import Protocol
from .connection import HTTPConnection
from .request import ClientRequest

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

    async def on_request(self):
        ...

    async def parse_request(self, data: bytes):
        self.request = ClientRequest(data)
        return self.request

    def __repr__(self) -> str:
        return '<HTTPProtcol>'


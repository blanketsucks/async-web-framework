from __future__ import annotations

from typing import Any, Optional, Dict, TYPE_CHECKING
from abc import ABC, abstractmethod
import copy
import ssl
import asyncio

from railway.utils import parse_headers
from railway.streams import StreamReader, StreamWriter
from railway.types import StrURL
from .errors import HookerAlreadyConnected, HookerClosed
from .response import HTTPResponse, HTTPStatus
from .request import HTTPRequest

if TYPE_CHECKING:
    from .sessions import HTTPSession

SSL_SCHEMES = ('https', 'wss')

__all__ = (
    'SSL_SCHEMES',
    'Hooker'
)

class Hooker(ABC):
    def __init__(self, session: HTTPSession) -> None:
        self.session = session
        self.reader: Optional[StreamReader] = None
        self.writer: Optional[StreamWriter] = None
        self.connected = False
        self.closed = False

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} closed={self.closed} connected={self.connected}>'

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self.session.loop

    @staticmethod
    def create_default_ssl_context() -> ssl.SSLContext:
        context = ssl.create_default_context()
        return context

    def ensure(self) -> None:
        if self.connected:
            raise HookerAlreadyConnected(hooker=self)

        if self.closed:
            raise HookerClosed(hooker=self)

    def copy(self):
        hooker = copy.copy(self)
        return hooker

    @abstractmethod
    async def connect(self, url: StrURL) -> None:
        raise NotImplementedError

    @abstractmethod
    async def write(self, data: Any) -> None:
        raise NotImplementedError

    def build_request(
        self, 
        method: str, 
        host: str, 
        path: str, 
        headers: Dict[str, Any],
        body: Optional[str]
    ) -> HTTPRequest:
        headers.setdefault('Connection', 'close')
        return HTTPRequest(method, path, host, headers, body)

    async def get_response(self) -> HTTPResponse:
        if self.reader is None:
            raise RuntimeError('Not connected')

        status_line = await self.reader.readuntil(b'\r\n')
        version, status_code, _ = status_line.decode().split(' ', 2)

        hdrs = await self.reader.readuntil(b'\r\n\r\n')

        status = HTTPStatus(int(status_code))
        headers: Dict[str, Any] = dict(parse_headers(hdrs))

        return HTTPResponse(
            hooker=self,
            status=status,
            version=version,
            headers=headers,
        )

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError
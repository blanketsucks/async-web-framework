from __future__ import annotations

import asyncio
import ssl
from typing import Any, Coroutine, Tuple, Type, Union, Dict, TypeVar, TYPE_CHECKING
from urllib.parse import urlparse
import copy
from socket import SocketKind, AddressFamily, gethostname

from .errors import HookerAlreadyConnected, HookerClosed
from .response import Response, HTTPStatus
from .request import Request
from atom.utils import find_headers
from atom.http.utils import AsyncIterator

if TYPE_CHECKING:
    from .client import HTTPSession

_T = TypeVar('_T')
SSL_SCHEMES = ('https', 'wss')

class Protocol(asyncio.Protocol):
    def __init__(self, client: Union['HTTPSession', 'WebsocketClient']) -> None:
        self.client = client

    def __call__(self):
        return self

    @property
    def loop(self):
        return self.client.loop

    def create_task(self, ret: Union[Coroutine[Any, Any, _T], _T]) -> 'Union[asyncio.Task[_T], _T]':
        if asyncio.iscoroutine(ret):
            return self.loop.create_task(ret)

        return ret

    async def push(self, data: bytes):
        raise NotImplementedError

    async def read(self):
        raise NotImplementedError

    async def wait(self):
        raise NotImplementedError

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def connection_lost(self, exc) -> None:
        if exc:
            raise exc
        
        self.transport = None

    def data_received(self, data: bytes) -> None:
        raise NotImplementedError

class Hooker:
    def __init__(self, client: Union[HTTPSession, WebsocketClient]) -> None:
        self.client = client

        self.connected = False
        self.closed = False

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} closed={self.closed} connected={self.connected}>'

    @property
    def loop(self):
        return self.client.loop

    def ensure(self):
        if self.connected:
            raise HookerAlreadyConnected('', hooker=self, client=self.client)

        if self.closed:
            raise HookerClosed('', hooker=self, client=self.client)

    def copy(self):
        hooker = copy.copy(self)
        return hooker

    def create_protocol(self, cls: Type[_T]) -> _T:
        return cls(self.client)

    def create_default_ssl_context(self):
        return ssl.create_default_context()

    def parse_host(self, url: str):
        parsed = urlparse(url)
        hostname = parsed.hostname

        if parsed.port:
            hostname = f'{parsed.hostname}:{parsed.port}'

        scheme = parsed.scheme
        is_ssl = False

        if scheme in SSL_SCHEMES:
            is_ssl = True

        return is_ssl, hostname, parsed.path or '/'

    async def create_connection(self, host: str):
        raise NotImplementedError

    async def create_ssl_connection(self, host: str):
        raise NotImplementedError

    async def read(self):
        raise NotImplementedError

    def write(self, data: bytes, *, transport: asyncio.Transport):
        transport.write(data)

    def build_request(self, 
                    method: str, 
                    host: str, 
                    path: str, 
                    headers: Dict,
                    body: str):
        headers.setdefault('Connection', 'close')
        return Request(method, path, host, headers, body)

    async def build_response(self, data: bytes=None):
        if not data:
            data = await self.read()
        
        headers, body = find_headers(data)
        header = next(headers)[0]

        version, status, description = header.split(' ', 2)

        status = HTTPStatus(int(status))
        headers = dict(headers)

        return Response(
            hooker=self,
            status=status,
            version=version,
            headers=headers,
            body=body
        )

    def getaddrinfo(self, 
                    host: str=None, 
                    port: int=None
                    ) -> AsyncIterator[Tuple[AddressFamily, SocketKind, int, str, Union[Tuple[str, int], Tuple[str, int, int, int]]]]:
        
        async def actual(host: str, port: int, loop: asyncio.AbstractEventLoop):
            if not host:
                host = gethostname()

            ret = await loop.getaddrinfo(host, port)
            return ret
            
        return AsyncIterator(actual(host, port, self.loop), host)

    def close(self):
        raise NotImplementedError
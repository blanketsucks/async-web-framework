from __future__ import annotations

import asyncio
import ssl
from typing import Any, Tuple, Optional, Union, Dict, TYPE_CHECKING
from urllib.parse import urlparse
import copy
from socket import SocketKind, AddressFamily, gethostname

from .errors import HookerAlreadyConnected, HookerClosed
from .response import Response, HTTPStatus
from .request import Request
from railway.utils import find_headers
from railway.http.utils import AsyncIterator

if TYPE_CHECKING:
    from .sessions import HTTPSession

SSL_SCHEMES = ('https', 'wss')

__all__ = (
    'SSL_SCHEMES',
    'Hooker'
)

class Hooker:
    def __init__(self, session: HTTPSession) -> None:
        self.session = session
        self._client = None

        self.connected = False
        self.closed = False

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} closed={self.closed} connected={self.connected}>'

    @property
    def loop(self):
        return self.session.loop

    def ensure(self):
        if self.connected:
            raise HookerAlreadyConnected(hooker=self, client=self.session)

        if self.closed:
            raise HookerClosed(hooker=self, client=self.session)

    def copy(self):
        hooker = copy.copy(self)
        return hooker

    def create_default_ssl_context(self):
        return ssl.create_default_context()

    def parse_host(self, url: str):
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            hostname = ''

        if parsed.port:
            hostname = f'{parsed.hostname}:{parsed.port}'

        scheme = parsed.scheme
        is_ssl = False

        if scheme in SSL_SCHEMES:
            is_ssl = True

        return is_ssl, hostname, parsed.path or '/'

    async def read(self) -> bytes:
        raise NotImplementedError

    async def write(self, data: Any) -> None:
        raise NotImplementedError

    def build_request(self, 
                    method: str, 
                    host: str, 
                    path: str, 
                    headers: Dict[str, Any],
                    body: Optional[str]):
        headers.setdefault('Connection', 'close')
        return Request(method, path, host, headers, body)

    async def build_response(self, data: Optional[bytes]=None):
        if not data:
            data = await self.read()
        
        hdrs, body = find_headers(data)
        header = next(hdrs)[0]

        version, status, _ = header.split(' ', 2)

        status = HTTPStatus(int(status)) # type: ignore
        headers: Dict[str, Any] = dict(hdrs) # type: ignore

        return Response(
            hooker=self,
            status=status,
            version=version,
            headers=headers,
            body=body
        )

    def getaddrinfo(self, 
                    host: Optional[str]=None, 
                    port: Optional[int]=None
                    ) -> AsyncIterator[Tuple[AddressFamily, SocketKind, int, str, Union[Tuple[str, int], Tuple[str, int, int, int]]]]:
        
        async def actual(host: Optional[str], port: Optional[int], loop: asyncio.AbstractEventLoop):
            if not host:
                host = gethostname()

            ret = await loop.getaddrinfo(host, port)
            return ret
            
        return AsyncIterator(actual(host, port, self.loop), host)

    async def close(self) -> None:
        raise NotImplementedError
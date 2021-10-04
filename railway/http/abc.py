"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations

import ssl
from typing import Any, Optional, Dict, TYPE_CHECKING
from urllib.parse import urlparse
import copy

from .errors import HookerAlreadyConnected, HookerClosed
from .response import HTTPResponse, HTTPStatus
from .request import HTTPRequest
from railway.utils import find_headers
from railway.streams import StreamTransport

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
        self.stream: Optional[StreamTransport] = None

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
            raise HookerAlreadyConnected(hooker=self)

        if self.closed:
            raise HookerClosed(hooker=self)

    def copy(self):
        hooker = copy.copy(self)
        return hooker

    def create_default_ssl_context(self):
        context = ssl.create_default_context()
        return context

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
        return HTTPRequest(method, path, host, headers, body)

    async def build_response(self, data: Optional[bytes]=None):
        if not data:
            data = await self.read()
        
        hdrs, body = find_headers(data)
        header = next(hdrs)[0]

        version, status, _ = header.split(' ', 2)

        status = HTTPStatus(int(status)) # type: ignore
        headers: Dict[str, Any] = dict(hdrs) # type: ignore

        return HTTPResponse(
            hooker=self,
            status=status,
            version=version,
            headers=headers,
            body=body
        )

    async def close(self) -> None:
        raise NotImplementedError
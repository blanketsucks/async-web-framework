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
import os
import base64

from typing import TYPE_CHECKING, Optional

import railway
from railway.utils import find_headers
from railway.websockets import (
    ClientWebsocket as Websocket,
    WebsocketCloseCode, 
)
from railway.response import HTTPStatus
from .request import HTTPRequest
from .abc import Hooker
from .errors import HandshakeError
from .response import HTTPResponse

if TYPE_CHECKING:
    from .sessions import HTTPSession

__all__ = (
    'Websocket',
    'TCPHooker',
    'WebsocketHooker'
)

class TCPHooker(Hooker):
    def __init__(self, session: 'HTTPSession') -> None:
        super().__init__(session)

    async def _create_connection(self, host: str):
        self.ensure()

        try:
            host, port = host.split(':')
        except ValueError:
            port = 80

        port = int(port)
        self.stream = await railway.open_connection(
            host=host,
            port=port
        )

        self.connected = True
        return self.stream
    
    async def _create_ssl_connection(self, host: str):
        self.ensure()
        context = self.create_default_ssl_context()

        try:
            host, port = host.split(':')
        except ValueError:
            port = 443

        port = int(port)
        self.stream = await railway.open_connection(
            host=host,
            port=port,
            ssl=context
        )

        self.connected = True
        return self.stream

    async def create_ssl_connection(self, host: str):
        client = await self._create_ssl_connection(host)
        return client

    async def create_connection(self, host: str):
        client = await self._create_connection(host)
        return client

    async def write(self, request: HTTPRequest):
        if not self.stream:
            raise RuntimeError('Not connected')

        await self.stream.write(request.encode())

    async def read(self) -> bytes:
        if not self.stream:
            return b''

        data = await self.stream.receive()
        return data

    async def close(self):
        if not self.stream:
            return

        await self.stream.close()
        
        self.connected = False
        self.closed = True

class WebsocketHooker(TCPHooker):
    def __init__(self, session: 'HTTPSession') -> None:
        super().__init__(session)

        self._task = None

    async def create_connection(self, host: str, path: str): # type: ignore
        await super().create_connection(host)
        ws = await self.handshake(path, host)

        return ws

    async def create_ssl_connection(self, host: str, path: str): # type: ignore
        await super().create_ssl_connection(host)
        ws = await self.handshake(path, host)

        return ws

    def generate_websocket_key(self):
        return base64.b64encode(os.urandom(16))

    def create_websocket(self): # type: ignore
        if not self.stream:
            return

        return Websocket(self.stream)
    
    async def handshake(self, path: str, host: str):
        if not self.stream:
            raise HandshakeError('Not connected', hooker=self)

        key = self.generate_websocket_key().decode()
        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': key,
            'Sec-WebSocket-Version': 13
        }

        request = self.build_request('GET', host, path, headers, None)
        await self.write(request)

        handshake = await self.stream.receive()
        response = await self.build_response(data=handshake)

        self.websocket = self.create_websocket()
        await self.verify_handshake(response)

        return self.websocket

    async def verify_handshake(self, response: HTTPResponse):
        headers = response.headers

        if response.status is not HTTPStatus.SWITCHING_PROTOCOLS:
            return await self._close(
                HandshakeError(
                    message=f"Expected status code '101', but received {response.status.value!r} instead",
                    hooker=self
                )
            )

        connection = headers.get('Connection')
        if connection is None or connection.lower() != 'upgrade':
            return await self._close(
                HandshakeError(
                    message=f"Expected 'Connection' header with value 'upgrade', but got {connection!r} instead",
                    hooker=self,
                )
            )

        upgrade = response.headers.get('Upgrade')
        if upgrade is None or upgrade.lower() != 'websocket':
            return await self._close(
                HandshakeError(
                    message=f"Expected 'Upgrade' header with value 'websocket', but got {upgrade!r} instead",
                    hooker=self,
                )
            )

    async def _close(self, exc: Exception):
        await self.close()
        raise exc

    async def close(self, *, data: Optional[bytes]=None, code: Optional[WebsocketCloseCode]=None) -> None:
        if not self.websocket:
            return

        if not code:
            code = WebsocketCloseCode.NORMAL

        if not data:
            data = b''

        return await self.websocket.close(data, code)

import asyncio
import os
import base64

from atom.http.hooker import TCPHooker
from atom.http.response import Response, HTTPStatus
from atom.http.errors import HandshakeError
from .websocket import Websocket
from .frame import WebsocketCloseCode
from .protocol import WebsocketProtocol

class WebsocketHooker(TCPHooker):
    def __init__(self, client) -> None:
        super().__init__(client)

        self.protocol = self.create_protocol(WebsocketProtocol)
        self._task = None

    async def create_connection(self, host: str, path: str):
        transport = await super().create_connection(host)
        ws = await self.handshake(path, host, transport=transport)

        return ws

    async def create_ssl_connection(self, host: str, path: str):
        transport = await super().create_ssl_connection(host)
        ws = await self.handshake(path, host, transport=transport)

        return ws

    def generate_websocket_key(self):
        return base64.b64encode(os.urandom(16))

    def create_websocket(self, transport: asyncio.Transport):
        return Websocket(transport, transport.get_extra_info('peername'))
    
    async def handshake(self, path: str, host: str, *, transport):
        key = self.generate_websocket_key().decode()
        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': key,
            'Sec-WebSocket-Version': 13
        }

        request = self.build_request('GET', host, path, headers)
        self.write(request.encode(), transport=transport)

        handshake = await self.protocol.wait_for_handshake()
        response = await self.build_response(data=handshake)

        self.websocket = self.create_websocket(transport)
        self.verify_handshake(response)

        self._task = self.loop.create_task(self.read())
        return self.websocket

    async def read(self):
        while True:
            data = await self.protocol.queue.get()
            self.websocket.reader.feed_data(data)

    def verify_handshake(self, response: Response):
        headers = response.headers

        if response.status is not HTTPStatus.SWITCHING_PROTOCOLS:
            return self._close(
                HandshakeError(f"Expected status code '101', but received {response.status.value!r} instead")
            )

        connection = headers.get('Connection')
        if connection is None or connection.lower() != 'upgrade':
            return self._close(
                HandshakeError(f"Expected 'Connection' header with value 'upgrade', but got {connection!r} instead")
            )

        upgrade = response.headers.get('Upgrade')
        if upgrade is None or upgrade.lower() != 'websocket':
            return self._close(
                HandshakeError(f"Expected 'Upgrade' header with value 'websocket', but got {upgrade!r} instead")
            )

    def _close(self, exc):
        self.close()
        raise exc

    def close(self, *, data: bytes=None, code: WebsocketCloseCode=None):
        if not code:
            code = WebsocketCloseCode.NORMAL

        if not data:
            data = b''

        self._task.cancel()
        return self.websocket.close(data, code)


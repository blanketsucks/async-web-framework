import os
import base64

from atom.utils import find_headers
from atom.websockets import (
    Websocket as _Websocket, 
    WebSocketCloseCode, 
    WebSocketFrame, 
    Data
)
from atom.client import Client
from atom.response import HTTPStatus, Response
from .request import Request
from .abc import Hooker
from .errors import HandshakeError

class Websocket(_Websocket):
    async def send_frame(self, frame):
        data = frame.encode(mask=True)
        await self._writer.write(data)

        return len(data)

    async def receive(self):
        opcode, raw, data = await WebSocketFrame.decode(self._reader.read, mask=False)
        return Data(raw, data), opcode

class TCPHooker(Hooker):
    def __init__(self, client) -> None:
        super().__init__(client)

    async def _create_connection(self, host: str):
        self.ensure()

        try:
            host, port = host.split(':')
        except ValueError:
            port = 80


        self._client = Client(host, int(port))
        await self._client.connect()

        self.connected = True
        return self._client
    
    async def _create_ssl_connection(self, host: str):
        self.ensure()
        context = self.create_default_ssl_context()

        try:
            host, port = host.split(':')
        except ValueError:
            port = 80

        port = 443

        self._client = Client(host, int(port), ssl_context=context)
        await self._client.connect()

        self.connected = True
        return self._client

    async def create_ssl_connection(self, host: str):
        client = await self._create_ssl_connection(host)
        return client

    async def create_connection(self, host: str):
        client = await self._create_connection(host)
        return client

    async def write(self, request: Request):
        await self._client.write(request.encode())

    async def read(self) -> bytes:
        if not self._client:
            return b''

        data = await self._client.receive()
        return data

    async def _read_body(self):
        data = await self.read()
        _, body = find_headers(data)

        return body

    async def close(self):
        await self._client.close()
        
        self.connected = False
        self.closed = True

class WebsocketHooker(TCPHooker):
    def __init__(self, client) -> None:
        super().__init__(client)

        self._task = None

    async def create_connection(self, host: str, path: str):
        await super().create_connection(host)
        ws = await self.handshake(path, host)

        return ws

    async def create_ssl_connection(self, host: str, path: str):
        await super().create_ssl_connection(host)
        ws = await self.handshake(path, host)

        return ws

    def generate_websocket_key(self):
        return base64.b64encode(os.urandom(16))

    def create_websocket(self):
        reader = self._client._protocol.reader
        writer = self._client._protocol.writer

        return Websocket(reader, writer)
    
    async def handshake(self, path: str, host: str):
        key = self.generate_websocket_key().decode()
        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': key,
            'Sec-WebSocket-Version': 13
        }

        request = self.build_request('GET', host, path, headers)
        await self.write(request)

        handshake = await self._client.receive()
        response = await self.build_response(data=handshake)

        self.websocket = self.create_websocket()
        await self.verify_handshake(response)

        return self.websocket

    async def verify_handshake(self, response: Response):
        headers = response.headers

        if response.status is not HTTPStatus.SWITCHING_PROTOCOLS:
            return await self._close(
                HandshakeError(f"Expected status code '101', but received {response.status.value!r} instead")
            )

        connection = headers.get('Connection')
        if connection is None or connection.lower() != 'upgrade':
            return await self._close(
                HandshakeError(f"Expected 'Connection' header with value 'upgrade', but got {connection!r} instead")
            )

        upgrade = response.headers.get('Upgrade')
        if upgrade is None or upgrade.lower() != 'websocket':
            return await self._close(
                HandshakeError(f"Expected 'Upgrade' header with value 'websocket', but got {upgrade!r} instead")
            )

    async def _close(self, exc):
        self.close()
        raise exc

    async def close(self, *, data: bytes=None, code: WebSocketCloseCode=None):
        if not code:
            code = WebSocketCloseCode.NORMAL

        if not data:
            data = b''

        return await self.websocket.close(data, code)

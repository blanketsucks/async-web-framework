import asyncio
from datetime import datetime
import typing
import hashlib
import base64

from .request import Request
from .response import Response, HTTPStatus
from .websockets import Websocket

if typing.TYPE_CHECKING:
    from .app import Application

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class ApplicationProtocol(asyncio.Protocol):
    def __init__(self, app: 'Application') -> None:
        self.app = app
        self.loop = app.loop
        self.websockets: typing.Mapping[typing.Tuple[str, int], Websocket] = {}

    def __call__(self):
        return self

    def is_websocket_request(self, request: Request):
        if request.method != 'GET':
            return False

        if request.version != 'HTTP/1.1':
            return False

        required = (
            'Host',
            'Upgrade',
            'Connection',
            'Sec-WebSocket-Version',
            'Sec-WebSocket-Key',
        )

        exists = all([header in request.headers for header in required])
        if not exists:
            return False

        for header in required:
            value: str = request.headers[header]

            if header == 'Upgrade':
                if value.lower() != 'websocket':
                    return False
                continue

            if header == 'Sec-WebSocket-Version':
                if value != '13':
                    return False
                continue

            if header == 'Sec-WebSocket-Key':
                key = base64.b64decode(value)

                if not len(key) == 16:
                    return False
                continue

        return True

    def parse_websocket_key(self, request: Request):
        key = request.headers['Sec-WebSocket-Key']

        sha1 = hashlib.sha1((key + GUID).encode()).digest()
        return base64.b64encode(sha1).decode()

    def handshake(self, request: Request):
        response = Response(status=HTTPStatus.SWITCHING_PROTOCOLS.status)
        key = self.parse_websocket_key(request)

        response.add_header(key='Upgrade', value='websocket')
        response.add_header(key='Connection', value='Upgrade')
        response.add_header(key='Sec-WebSocket-Accept', value=key)

        self.transport.write(response.encode())

    def handle_request(self, request, websocket):
        return self.loop.create_task(
            coro=self.app._request_handler(request, websocket=websocket)
        )

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def feed_into_websocket(self, data: bytes):
        peer = self.transport.get_extra_info('peername')
        websocket = self.websockets[peer]

        websocket.feed_data(data)

    def data_received(self, data: bytes) -> None:
        try:
            request = Request.parse(data, self, datetime.utcnow())
        except ValueError:
            return self.feed_into_websocket(data)
            
        websocket = Websocket(self.transport, None)

        if self.is_websocket_request(request):
            peer = self.transport.get_extra_info('peername')
            self.websockets[peer] = websocket

            self.handshake(request)

        self.handle_request(request, websocket)
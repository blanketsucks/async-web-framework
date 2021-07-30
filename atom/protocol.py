from typing import TYPE_CHECKING, Dict, Tuple, Optional
import asyncio
import hashlib
import base64

from .request import Request
from .response import Response, HTTPStatus
from .websockets import Websocket

if TYPE_CHECKING:
    from .app import Application

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class ApplicationProtocol(asyncio.Protocol):
    def __init__(self, app: 'Application') -> None:
        self.app = app
        self.loop = app.loop
        self.websockets: Dict[Tuple[str, int], Websocket] = {}

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
        self.app.dispatch('connection', transport, transport.get_extra_info('peername'))

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            raise exc

    def store_websocket(self, ws: Websocket):
        peer = self.transport.get_extra_info('peername')
        self.websockets[peer] = ws

    def get_websocket(self):
        peer = self.transport.get_extra_info('peername')
        websocket = self.websockets[peer]

        return websocket

    def feed_into_websocket(self, data: bytes):
        websocket = self.get_websocket()
        websocket.feed_data(data)

    def ensure_websockets(self):
        self.app._ensure_websockets()
        
        for peer, websocket in self.websockets.items():
            if websocket.is_closed():
                self.websockets.pop(peer)

    def data_received(self, data: bytes) -> None:
        self.ensure_websockets()
        
        try:
            request = Request.parse(data, self)
        except ValueError:
            self.app.dispatch('websocket_data_receive', data)
            return self.feed_into_websocket(data)

        self.app.dispatch('request', data)
        
        peer = self.transport.get_extra_info('peername')
        websocket = Websocket(self.transport, peer=peer)

        if self.is_websocket_request(request):
            self.store_websocket(websocket)
            self.handshake(request)

        self.request = self.handle_request(request, websocket)
        self.request.add_done_callback(lambda task: setattr(self, 'request', None))

        self.app.log(f'{request.method} request at {request.url.path}')
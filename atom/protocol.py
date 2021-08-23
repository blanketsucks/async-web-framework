import logging
from typing import TYPE_CHECKING, Dict, Tuple, Optional
import asyncio
import hashlib
import base64
from asyncio.trsock import TransportSocket

from .request import Request
from .response import Response, HTTPStatus
from .websockets import Websocket

if TYPE_CHECKING:
    from .app import Application

log = logging.getLogger(__name__)

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class Connection:
    def __init__(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self._closed = False

    @property
    def socket(self) -> TransportSocket:
        return self.transport.get_extra_info('socket')

    @property
    def peername(self) -> Tuple[str, int]:
        return self.transport.get_extra_info('peername')

    @property
    def sockname(self) -> Tuple[str, int]:
        return self.transport.get_extra_info('sockname')

    def is_closed(self) -> bool:
        return self._closed

    def get_protocol(self):
        return self.transport.get_protocol()

    def close(self):
        self.transport.close()
        self._closed = True

    def write(self, data: bytes):
        log.info(f"Writing {len(data)} bytes to {self.peername}")
        self.transport.write(data)

class ApplicationProtocol:
    def __init__(self, app: 'Application') -> None:
        self.app = app
        self.loop = app.loop
        self.websockets: Dict[Tuple[str, int], Websocket] = {}
        self.connections: Dict[Tuple[str, int], Connection] = {}

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
        key: str = request.headers['Sec-WebSocket-Key']

        sha1 = hashlib.sha1((key + GUID).encode()).digest()
        return base64.b64encode(sha1).decode()

    def handshake(self, request: Request):
        response = Response(status=HTTPStatus.SWITCHING_PROTOCOLS.status)
        key = self.parse_websocket_key(request)

        response.add_header(key='Upgrade', value='websocket')
        response.add_header(key='Connection', value='Upgrade')
        response.add_header(key='Sec-WebSocket-Accept', value=key)

        self.connection.write(response.encode())

    def handle_request(self, request, websocket) -> 'asyncio.Task[bytes]':
        task = self.loop.create_task(
            coro=self.app._request_handler(request, self.connection, websocket=websocket)
        )
        return task

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.connection = connection = Connection(transport)
        log.info(f'Connection made from {connection.peername}')

        self.app.dispatch('connection', connection)

        peer = connection.peername
        self.connections[peer] = connection

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            raise exc

        peer = self.connection.peername
        log.info(f'Connection lost from {peer}')

        self.app.dispatch('connection_lost', self.connection)
        self.connections.pop(peer, None)

    def store_websocket(self, ws: Websocket):
        peer = self.connection.peername
        self.websockets[peer] = ws

    def get_websocket(self):
        peer = self.connection.peername
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
        log.info(f'Received {len(data)} bytes from {self.connection.peername}')
        self.ensure_websockets()
        
        try:
            request = Request.parse(data, self)
        except ValueError:
            self.app.dispatch('websocket_data_receive', data)
            return self.feed_into_websocket(data)

        self.app.dispatch('request', data)
        
        peer = self.connection.peername
        websocket = Websocket(self.connection)

        if self.is_websocket_request(request):
            self.store_websocket(websocket)
            self.handshake(request)

        self.handle_request(request, websocket)
        log.info(f'{request.method} request at {request.url.path} from {peer!r}')
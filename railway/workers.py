from __future__ import annotations
import asyncio
from typing import Dict, Optional, Tuple, TYPE_CHECKING
import hashlib
import base64
import logging
import datetime

from .server import Server, ClientConnection
from .websockets import ServerWebsocket as Websocket
from .request import Request
from .response import Response
from .responses import SwitchingProtocols

if TYPE_CHECKING:
    from .app import Application

__all__ = (
    'GUID',
    'Worker'
)

log = logging.getLogger(__name__)

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class Worker:
    def __init__(self, app: Application, id: int):
        self.app = app
        self.id = id
        self.websockets: Dict[Tuple[str, int], Websocket] = {}

        self.current_task = None
        self._working = False
        self.server = None

        self.socket = app.socket

    def __repr__(self) -> str:
        return '<Worker id={0.id}>'.format(self)

    @property
    def port(self):
        return self.app.port

    @property
    def host(self):
        return self.app.host

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return self.app.loop

    def is_working(self):
        return self._working

    def is_serving(self):
        return self.server is not None and self.server.is_serving()

    async def start(self, loop: asyncio.AbstractEventLoop):
        self.server = Server(
            host=self.host, 
            port=self.port,
            ipv6=self.app.is_ipv6(), 
            loop=loop, 
            is_ssl=self.app.is_ssl, 
            ssl_context=self.app.ssl_context
        )

        await self.server.serve(sock=self.socket) # type: ignore
        self.app.dispatch('worker_startup', self)

    async def run(self, loop: asyncio.AbstractEventLoop):
        await self.start(loop=loop)

        if not self.server or not self.loop:
            return

        log.info(f'[Worker-{self.id}] Started serving.')

        while True:
            connection = await self.server.accept()
            self.loop.create_task(
                coro=self.handler(connection),
                name=f'Worker-{self.id}-{connection.peername}'
            )

    async def stop(self):
        if not self.server:
            return

        self.ensure_websockets()
        await self.server.close()

        self.app.dispatch('worker_shutdown', self)
        log.info(f'[Worker-{self.id}] Stopped serving.')

    def get_websocket(self, connection: ClientConnection):
        peer = connection.peername
        websocket = self.websockets.get(peer)

        return websocket

    def store_websocket(self, ws: Websocket, connection: ClientConnection):
        peer = connection.peername
        self.websockets[peer] = ws

    def feed_into_websocket(self, data: bytes, connection: ClientConnection):
        websocket = self.get_websocket(connection)
        if not websocket:
            return None

        log.debug(f'[Worker-{self.id}] Feeding {len(data)} bytes into {websocket}')
        websocket.feed_data(data)

        return data

    def ensure_websockets(self):
        self.app._ensure_websockets() # type: ignore
        
        for peer, websocket in self.websockets.items():
            if websocket.is_closed():
                self.websockets.pop(peer)

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

    async def handshake(self, request: Request, connection: ClientConnection):
        response = SwitchingProtocols()
        key = self.parse_websocket_key(request)

        response.add_header(key='Upgrade', value='websocket')
        response.add_header(key='Connection', value='Upgrade')
        response.add_header(key='Sec-WebSocket-Accept', value=key)

        await self.write(response, connection)

    async def write(self, data: Response, connection: ClientConnection):
        return await connection.write(data.encode())

    async def handler(self, connection: ClientConnection):
        self._working = True
        
        data = await connection.receive()
        created_at = datetime.datetime.utcnow()
        
        log.info(f'[Worker-{self.id}] Received {len(data)} bytes from {connection.peername}')

        try:
            request = Request.parse(data, self.app, connection, self, created_at)
        except ValueError:
            data = self.feed_into_websocket(data, connection)

            if not data:
                await connection.close()
                return

            self.app.dispatch('websocket_data_receive', data, self)

        self.app.dispatch('raw_request', data, self)
        self.app.dispatch('request', request, self)

        log.info(f'[Worker-{self.id}] Received a {request.method!r} request to {request.url.path!r} from {connection.peername}')
        
        websocket = Websocket(connection._reader, connection._writer) # type: ignore

        if self.is_websocket_request(request):
            self.store_websocket(websocket, connection)
            await self.handshake(request, connection)

        await self.app._request_handler( # type: ignore
            request=request,
            websocket=websocket,
            connection=connection,
            worker=self
        )

        self._working = False


        
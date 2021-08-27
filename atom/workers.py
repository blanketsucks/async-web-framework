from __future__ import annotations
import asyncio
from typing import Dict, Optional, Tuple, TYPE_CHECKING, Union
import hashlib
import base64
import logging
import datetime

from .server import Server, ClientConnection
from .websockets import Websocket
from .request import Request
from .response import Response
from .responses import SwitchingProtocols
from .abc import AbstractWorker

if TYPE_CHECKING:
    from .app import Application

log = logging.getLogger(__name__)

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class Worker(AbstractWorker):
    def __init__(self, app: Application, id: int):
        self.app = app
        self.id = id
        self.websockets: Dict[Tuple[str, int], Websocket] = {}

        self.current_task = None
        self._working = False
        self.server = None

    def __repr__(self) -> str:
        return '<Worker id={0.id}>'.format(self)

    @property
    def socket(self):
        return self.app.socket
    
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
        self.server = Server(self.host, self.port, loop=loop)

        await self.server.serve(sock=self.app._socket)
        self.app.dispatch('worker_startup', self)

        log.debug(f'Started worker {self.id}')

    async def run(self, loop: asyncio.AbstractEventLoop):
        await self.start(loop=loop)

        while True:
            connection = await self.server.accept()
            if not connection:
                continue

            self.current_task = self.loop.create_task(
                coro=self.handler(connection),
                name=f'Worker-{self.id}-{connection.peername}'
            )

    async def stop(self):
        if self.current_task:
            await self.current_task
            self.current_task = None

        self.ensure_websockets()
        await self.server.close()

        self.app.dispatch('worker_shutdown', self)
        log.debug(f'Stopped worker {self.id}')

    def get_websocket(self, connection: ClientConnection):
        peer = connection.peername
        websocket = self.websockets[peer]

        return websocket

    def store_websocket(self, ws: Websocket, connection: ClientConnection):
        peer = connection.peername
        self.websockets[peer] = ws

    def feed_into_websocket(self, data: bytes, connection: ClientConnection):
        websocket = self.get_websocket(connection)

        log.debug(f'Feeding {len(data)} bytes into {websocket}')
        websocket.feed_data(data)

    def ensure_websockets(self):
        self.app._ensure_websockets()
        
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
        
        log.info(f'Received {len(data)} bytes from {connection.peername}')

        try:
            request = Request.parse(data, self.app, connection, self, created_at)
        except ValueError:
            self.app.dispatch('websocket_data_receive', data, self)
            return self.feed_into_websocket(data, connection)

        self.app.dispatch('raw_request', data, self)
        self.app.dispatch('request', request, self)

        log.info(f'Received a {request.method} request to {request.url.path} from {connection.peername}')
        
        websocket = Websocket(connection._reader, connection._writer)

        if self.is_websocket_request(request):
            self.store_websocket(websocket, connection)
            await self.handshake(request)

        await self.app._request_handler(
            request=request,
            websocket=websocket,
            connection=connection,
            worker=self
        )

        self._working = False


        

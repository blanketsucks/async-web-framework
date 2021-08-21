import socket
from typing import Dict, Tuple, TYPE_CHECKING
import hashlib
import base64

from .server import Server, ClientConnection
from .websockets import Websocket
from .request import Request
from .response import Response, HTTPStatus

if TYPE_CHECKING:
    from .app import Application

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class Worker:
    def __init__(self, app: 'Application', sock: socket.socket):
        self.app = app
        self.socket = sock

        self.websockets: Dict[Tuple[str, int], Websocket] = {}

        self._working = False
        self.server = Server(self.host, self.port, loop=app.loop)
    
    @property
    def port(self):
        return self.app.port

    @property
    def host(self):
        return self.app.host

    def is_working(self):
        return self._working

    async def start(self):
        await self.server.serve(sock=self.socket)

    async def run(self):
        await self.start()

        while True:
            connection = await self.server.accept()
            await self.handle(connection)

    async def stop(self):
        self.ensure_websockets()
        await self.server.close()

    def get_websocket(self, connection: ClientConnection):
        peer = connection.peername
        websocket = self.websockets[peer]

        return websocket

    def store_websocket(self, ws: Websocket, connection: ClientConnection):
        peer = connection.peername
        self.websockets[peer] = ws

    def feed_into_websocket(self, data: bytes, connection: ClientConnection):
        websocket = self.get_websocket(connection)
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
        response = Response(status=HTTPStatus.SWITCHING_PROTOCOLS.status)
        key = self.parse_websocket_key(request)

        response.add_header(key='Upgrade', value='websocket')
        response.add_header(key='Connection', value='Upgrade')
        response.add_header(key='Sec-WebSocket-Accept', value=key)

        await connection.write(response.encode())

    async def handle(self, connection: ClientConnection):
        self._working = True

        data = await connection.receive()

        try:
            request = Request.parse(data, self.app, connection.peername)
        except ValueError:
            self.app.dispatch('websocket_data_receive', data)
            return self.feed_into_websocket(data, connection)

        self.app.dispatch('request', data)
        
        peer = connection.peername
        websocket = Websocket(connection)

        if self.is_websocket_request(request):
            self.store_websocket(websocket, connection)
            await self.handshake(request)

        await self.app._request_handler(
            request=request,
            websocket=websocket,
            connection=connection,
        )


        

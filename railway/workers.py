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
import asyncio
from typing import Dict, Optional, Tuple, TYPE_CHECKING
import hashlib
import base64
import logging
import datetime
import socket as _socket

from .server import TCPServer, ClientConnection
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
    """
    A worker class used by the application to handle requests.
    This class is responsible for handling requests from clients and forwarding them to the application. 
    It also handles incoming websocket requests.

    Parameters
    ----------
    app: :class:`~railway.app.Application`
        The application instance.
    id: :class:`int`
        The id of the worker.

    Attributes
    ----------
    app: :class:`railway.app.Application`
        The application instance.
    id: :class:`int`
        The id of the worker.
    websockets: Dict[:class:`tuple`, :class:`railway.websockets.ServerWebsocket`]
        A dictionary of websocket connections.
    socket: :class:`socket.socket`
        the socket used by the worker.
    """
    def __init__(self, app: Application, id: int, max_pending_connections: int=200, connection_timeout: int=None):
        self.app: Application = app
        self.id: int = id
        self.websockets: Dict[Tuple[str, int], Websocket] = {}

        self.current_task = None
        self._working = False
        self._ready = asyncio.Event()
        self.server = None
        self.max_pending_connections = max_pending_connections
        self.connection_timeout = connection_timeout
        self.socket: _socket.socket = app.socket

    def __repr__(self) -> str:
        return '<Worker id={0.id}>'.format(self)

    @property
    def port(self) -> int:
        """
        The port of the worker.
        """
        return self.app.port

    @property
    def host(self) -> str:
        """
        The host of the worker.
        """
        return self.app.host

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """
        The event loop of the worker.
        """
        return self.app.loop

    def is_working(self) -> bool:
        """
        True if the worker is currently handling a request.
        """
        return self._working

    def is_serving(self) -> bool:
        """
        True if the worker is currently serving requests.
        """
        return self.server is not None and self.server.is_serving()

    async def wait_until_ready(self):
        """
        Waits until the worker is fully ready to serve requests.
        """
        await self._ready.wait()

    async def start(self):
        """
        Starts the worker.
        This function does not begin the serving of requests.
        """
        self.server = TCPServer(
            host=self.host, 
            port=self.port,
            ipv6=self.app.is_ipv6(), 
            loop=self.loop, 
            is_ssl=self.app.is_ssl(),
            max_connections=self.max_pending_connections,
            ssl_context=self.app.ssl_context
        )

        await self.server.serve(sock=self.socket) # type: ignore
        self.app.dispatch('worker_startup', self)

    async def run(self):
        """
        Starts the worker and begins serving requests.
        """ 
        await self.start()

        if not self.server or not self.loop:
            return

        log.info(f'[Worker-{self.id}] Started serving.')
        self._ready.set()

        while True:
            connection = await self.server.accept()
            if not connection:
                continue

            self.loop.create_task(
                coro=self.handler(connection),
                name=f'Worker-{self.id}-{connection.peername}'
            )

    async def stop(self):
        """
        Stops the worker.
        """
        if not self.server:
            return

        self.ensure_websockets()
        
        await self.server.close()
        self.server = None

        self._ready.clear()
        self.app.dispatch('worker_shutdown', self)
        log.info(f'[Worker-{self.id}] Stopped serving.')

    async def close(self):
        """
        An alias for :meth:`~railway.workers.Worker.stop`.
        """
        await self.stop()

    def get_websocket(self, connection: ClientConnection) -> Optional[Websocket]:
        """
        Gets the websocket associated with the given connection.

        Parameters
        ----------
        connection: :class:`~railway.server.ClientConnection`
            The connection to get the websocket for.
        """
        peer = connection.peername
        websocket = self.websockets.get(peer)

        return websocket

    def store_websocket(self, ws: Websocket, connection: ClientConnection) -> None:
        """
        Saves the websocket to the internal dictionary.

        Parameters
        ----------
        ws: :class:`~railway.websockets.websocket.ServerWebsocket`
            The websocket to save.
        connection: :class:`~railway.server.ClientConnection`
            The connection to save the websocket for.
        """
        peer = connection.peername
        self.websockets[peer] = ws

    def feed_into_websocket(self, data: bytes, connection: ClientConnection) -> Optional[bytes]:
        """
        Feeds the given data into the websocket associated with the given connection.

        Parameters
        ----------
        data: :class:`bytes`
            The data to feed into the websocket.
        connection: :class:`~railway.server.ClientConnection`
            The connection to feed the data into the websocket for.
        """
        websocket = self.get_websocket(connection)
        if not websocket:
            return None

        log.debug(f'[Worker-{self.id}] Feeding {len(data)} bytes into {websocket}')
        websocket.feed_data(data)

        return data

    def ensure_websockets(self) -> None:
        """
        Ensures that all websockets that are saved inside the internal dictionary are not closed.
        If a websocket is closed, it is removed from the dictionary.
        """
        self.app._ensure_websockets() # type: ignore
        
        for peer, websocket in self.websockets.items():
            if websocket.is_closed():
                self.websockets.pop(peer)

    def is_websocket_request(self, request: Request) -> bool:
        """
        Verifies if the given request is a websocket request.

        Parameters
        ----------
        request: :class:`~railway.server.Request`
            The request to verify.
        """
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

    def parse_websocket_key(self, request: Request) -> str:
        """
        Parses the websocket key from the given request.

        Parameters
        ----------
        request: :class:`~railway.request.Request`
            The request to parse the websocket key from.
        """
        key: str = request.headers['Sec-WebSocket-Key']

        sha1 = hashlib.sha1((key + GUID).encode()).digest()
        return base64.b64encode(sha1).decode()

    async def handshake(self, request: Request, connection: ClientConnection) -> None:
        """
        Performs a websocket handshake.

        Parameters
        ----------
        request: :class:`railway.request.Request`
            The request to perform the websocket handshake for.
        connection: :class:`~railway.server.ClientConnection`
            The connection to perform the websocket handshake for.
        """
        response = SwitchingProtocols()
        key = self.parse_websocket_key(request)

        response.add_header(key='Upgrade', value='websocket')
        response.add_header(key='Connection', value='Upgrade')
        response.add_header(key='Sec-WebSocket-Accept', value=key)

        await self.write(response, connection)

    async def write(self, data: Response, connection: ClientConnection):
        return await connection.write(data.encode())

    async def handler(self, connection: ClientConnection) -> None:
        """
        This function gets called whenever a new connection gets made.
        """
        self._working = True

        data = await connection.receive(timeout=self.connection_timeout)
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
            return

        self.app.dispatch('raw_request', data, self)
        self.app.dispatch('request', request, self)

        log.info(f'[Worker-{self.id}] Received a {request.method!r} request to {request.url.path!r} from {connection.peername}')
        
        websocket = Websocket(connection._transport) # type: ignore

        if self.is_websocket_request(request):
            self.store_websocket(websocket, connection)
            await self.handshake(request, connection)

        await self.app._request_handler( # type: ignore
            request=request,
            websocket=websocket,
        )

        self._working = False


        

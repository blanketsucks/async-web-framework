import asyncio
from .protocols import Protocol
from . import sockets
from .import websockets
from .transports import Transport, WebsocketTransport

import socket

class Server:
    def __init__(self, protocol: Protocol, host: str, port: int, backlog: int) -> None:
        
        self.protocol = protocol
        self.host = host
        self.port = port
        self.backlog = backlog

        self._loop = asyncio.get_event_loop()

        self._create_socket()

    def _create_socket(self):
        self.socket = sockets.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _create_transport(self, client):
        transport = Transport(
            socket=client,
            protocol=self.protocol,
            loop=self._loop
        )

        return transport

    async def __handler(self, client: sockets.socket, transport: Transport):
        data = await client.recvall(32768)
        transport._data_received(data)

    async def start(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        await self.socket.bind(self.host, self.port)
        await self.socket.listen(self.backlog)

    async def serve(self):
        await self.start()

        while True:
            client, addr = await self.socket.accept()            
            transport = Transport(
                socket=client,
                protocol=self.protocol,
                loop=self._loop
            )

            self._loop.create_task(self.__handler(client, transport))

    def close(self):
        return self.socket.shutdown(socket.SHUT_RDWR)

class WebsocketServer(Server):
    
    def _create_socket(self):
        self.socket = websockets.Websocket(socket.AF_INET, socket.SOCK_STREAM)

    def _create_transport(self, client):
        return WebsocketTransport(
            socket=client,
            protocol=self.protocol,
            loop=self._loop,
            future=None
        )

    async def _handler(self, client: websockets.Websocket, transport: WebsocketTransport):
        await transport._data_received()

    async def serve(self):
        await self.start()

        while True:
            client, addr = await self.socket.accept(do_handshake_on_connect=False)
            transport = self._create_transport(client)

            self._loop.create_task(self._handler(client, transport))
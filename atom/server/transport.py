import socket
import asyncio

from .bases import Transport
from .connection import HTTPConnection
from .protocol import HTTPProtocol

class HTTPTransport(Transport):
    def __init__(self, __socket: socket.socket, __loop: asyncio.AbstractEventLoop, __protocol: HTTPProtocol) -> None:
        self.socket = __socket
        self.loop = __loop
        self.protocol = __protocol

    async def call_protocol(self, name: str, *args):
        actual = 'on_' + name
        method = getattr(self.protocol, actual, None)

        await method(*args)

    async def listen(self):
        self.socket.listen(5)

        while True:
            client, address = await self.loop.sock_accept(self.socket)
            client.settimeout(60)

            info = {
                'loop': self.loop,
                'socket': client,
                'transport': self
            }

            conn = HTTPConnection(info)
            await self.call_protocol('connection_made', conn)

            self.loop.create_task(
                self.handle(client, address)
            )

    async def handle(self, client: socket.socket, address):
        PACKET_SIZE = 1024
        while True:
            data = await self.loop.sock_recv(client, PACKET_SIZE)

            await self.call_protocol('socket_receive', data)
            await self.call_protocol('request')

            client.close()
            break
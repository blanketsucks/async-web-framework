import asyncio
import typing

from .bases import Transport
from .connection import HTTPConnection
from .protocol import HTTPProtocol
from .sockets import HTTPSocket, Address

__all__ = (
    'HTTPTransport',
)

class HTTPTransport(Transport):
    def __init__(self, __socket: HTTPSocket, __loop: asyncio.AbstractEventLoop, __protocol: HTTPProtocol) -> None:
        self.socket = __socket
        self.loop = __loop
        self.protocol = __protocol

        self.clients: typing.List[HTTPSocket] = []
        self.client_tasks: typing.List[asyncio.Task] = []

    async def call_protocol(self, name: str, *args):
        actual = 'on_' + name
        method = getattr(self.protocol, actual, None)

        await method(*args)

    async def listen(self):
        await self.socket.listen(5)

        print('?')
        while True:
            print('before accept')
            client, address = await self.socket.accept()
            print(client, address)

            self.clients.append(client)
            client.settimeout(5)

            peername = await client.getpeername()
            sockname = await client.getsockname()

            conn = HTTPConnection(
                loop=self.loop,
                protocol=self.protocol,
                transport=self,
                socket=client,
                address=address,
                peername=peername,
                sockname=sockname
            )

            await self.call_protocol('connection_made', conn)

            task = self.loop.create_task(
                self.handle(client, address)
            )
            self.client_tasks.append(task)

    async def handle(self, client: HTTPSocket, address: Address):
        PACKET_SIZE = 1024
        try:
            body, headers, data = await client.receive(PACKET_SIZE)

            await self.call_protocol('data_receive', data)
            await self.call_protocol('request', body, headers)

        except Exception as exc:
            await self.call_protocol('connection_lost', exc)
            client.close()

        else:
            await self.call_protocol('connection_lost')
            client.close()


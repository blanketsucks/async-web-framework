import asyncio
import typing

from atom.utils import find_headers
from .protocol import HTTPProtocol
from .request import Request
from .abc import Hooker

class TCPHooker(Hooker):
    def __init__(self, client) -> None:
        super().__init__(client)

        self.protocol = self.create_protocol(HTTPProtocol)

    async def _create_connection(self, host: str) -> typing.Tuple[asyncio.Transport, HTTPProtocol]:
        self.ensure()

        try:
            host, port = host.split(':')
        except ValueError:
            port = 80

        transport, protocol = await self.loop.create_connection(
            self.protocol,
            host,
            port
        )

        self.connected = True
        return transport, protocol
    
    async def _create_ssl_connection(self, host: str):
        self.ensure()

        context = self.create_default_ssl_context()
        hostname = host
        port = 443

        transport, protocol = await self.loop.create_connection(
            self.protocol,
            host,
            port,
            ssl=context,
            server_hostname=hostname
        )

        self.connected = True
        return transport, protocol

    async def create_ssl_connection(self, host: str):
        transport, protocol = await self._create_ssl_connection(host)
        return transport

    async def create_connection(self, host: str):
        transport, protocol = await self._create_connection(host)
        return transport

    def write(self, request: Request, *, transport: asyncio.Transport):
        transport.write(request.encode())

    async def read(self):
        await self.protocol.wait()
        buffer = bytearray()
        
        while not self.protocol.queue.empty():
            data = await self.protocol.read()
            buffer += data

        return bytes(buffer)

    async def _read_body(self):
        data = await self.read()
        _, body = find_headers(data)

        return body

    def close(self):
        self.protocol.transport.close()
        
        self.connected = False
        self.closed = True
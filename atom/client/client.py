import asyncio
import ssl
from typing import Union, List

from atom.stream import StreamWriter, StreamReader
from atom import compat

class ClientProtocol(asyncio.Protocol):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

        self.reader = None
        self.writer = None

        self.waiter = None

    def __call__(self):
        return self

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.reader = StreamReader()
        self.writer = StreamWriter(transport)

        self.waiter = self.loop.create_future()

    def data_received(self, data: bytes) -> None:
        self.reader.feed_data(data)

    def pause_writing(self) -> None:
        writer = self.writer
        writer._waiter = self.loop.create_future()
    
    def resume_writing(self) -> None:
        writer = self.writer

        if writer._waiter:
            writer._waiter.set_result(None)

    def connection_lost(self, exc: Exception) -> None:
        if exc:
            raise exc

        self.waiter.set_result(None)
        self.waiter = None

class Client:
    def __init__(self, 
                host: str, 
                port: int, 
                *, 
                ssl_context: ssl.SSLContext=None,
                loop: asyncio.AbstractEventLoop=None) -> None:
        self.host = host
        self.port = port

        self.ssl_context = ssl_context
        self.loop = loop or compat.get_running_loop()

        self._protocol = None
        self._connected = False

    def __repr__(self) -> str:
        return f'<Client host={self.host!r} port={self.port}>'

    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, *args):
        return await self.close()

    def is_connected(self):
        return self._connected and self._protocol is not None

    def is_ssl(self):
        return self.ssl_context is not None and isinstance(self.ssl_context, ssl.SSLContext)

    async def connect(self):
        self._protocol = protocol = ClientProtocol(self.loop)
        pair = await self.loop.create_connection(
            protocol, self.host, self.port, ssl=self.ssl_context
        )

        self._connected = True
        return self

    async def write(self, data: Union[bytearray, bytes]):
        if not self.is_connected():
            raise RuntimeError('Not connected')

        await self._protocol.writer.write(data)
    
    async def writelines(self, data: List[Union[bytearray, bytes]]):
        if not self.is_connected():
            raise RuntimeError('Not connected')

        await self._protocol.writer.writelines(data)

    async def receive(self, nbytes: int=None):
        if not self.is_connected():
            raise RuntimeError('Not connected')
        
        return await self._protocol.reader.read(nbytes)

    async def close(self):
        if not self.is_connected():
            raise RuntimeError('Not connected')

        self._protocol.writer.close()
        await self._protocol.waiter

        return self

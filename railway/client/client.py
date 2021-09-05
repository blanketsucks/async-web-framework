import asyncio
import ssl
from typing import Any, Union, List, Optional
import socket

from railway.stream import StreamWriter, StreamReader
from railway import compat

__all__ = (
    'ClientProtocol', 
    'Client', 
    'create_connection'
)

class ClientProtocol(asyncio.Protocol):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

        self.reader = None
        self.writer = None

        self.waiter = None

    def __call__(self):
        return self

    def connection_made(self, transport: asyncio.Transport) -> None: # type: ignore
        self.reader = StreamReader()
        self.writer = StreamWriter(transport)

        self.waiter = self.loop.create_future()

    def data_received(self, data: bytes) -> None:
        if not self.reader:
            return

        self.reader.feed_data(data)

    def pause_writing(self) -> None:
        if not self.writer:
            return

        writer = self.writer
        writer._waiter = self.loop.create_future() # type: ignore
    
    def resume_writing(self) -> None:
        if not self.writer:
            return

        writer = self.writer

        if writer._waiter: # type: ignore
            writer._waiter.set_result(None) # type: ignore

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            raise exc

        if not self.waiter:
            return

        self.waiter.set_result(None)
        self.waiter = None

    async def wait_for_close(self):
        if self.waiter:
            await self.waiter

class Client:
    def __init__(self, 
                host: Optional[str]=None, 
                port: Optional[int]=None, 
                *,
                sock: Optional[socket.socket]=None, 
                ssl_context: Optional[Union[ssl.SSLContext, Any]]=None,
                loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        self.host = host
        self.port = port

        if sock:
            if host or port:
                raise ValueError('Both host and port must be None if sock is specified')

        self.sock = sock

        self.ssl_context = ssl_context
        self.loop = loop or compat.get_running_loop()

        self._protocol = None

        self._closed = False
        self._connected = False

    def __repr__(self) -> str:
        reprs: List[str] = ['<Client']

        for attr in ('host', 'port', 'is_ssl', 'is_connected', 'is_closed'):
            value = getattr(self, attr)

            if callable(value):
                value = value()

            reprs.append(f'{attr}={value!r}')

        return ' '.join(reprs) + '>'

    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, *args: Any):
        return await self.close()

    def __await__(self):
        return self.connect().__await__()

    def _ensure_connection(self):
        if not self.is_connected():
            raise RuntimeError('Client not connected')

        if self.is_closed():
            raise RuntimeError('Client is closed')

    def is_connected(self):
        return self._connected and self._protocol is not None

    def is_closed(self):
        return self._closed

    def is_ssl(self):
        return self.ssl_context is not None and isinstance(self.ssl_context, ssl.SSLContext)

    async def connect(self):
        self._protocol = protocol = ClientProtocol(self.loop)
        await self.loop.create_connection(
            protocol, self.host, self.port, sock=self.sock, ssl=self.ssl_context
        )

        self._connected = True
        return self

    async def write(self, data: Union[bytearray, bytes]):
        self._ensure_connection()
        await self._protocol.writer.write(data) # type: ignore
    
    async def writelines(self, data: List[Union[bytearray, bytes]]):
        self._ensure_connection()
        await self._protocol.writer.writelines(data) # type: ignore

    async def receive(self, nbytes: Optional[int]=None):
        self._ensure_connection()
        return await self._protocol.reader.read(nbytes) # type: ignore

    async def close(self):
        self._ensure_connection()

        self._protocol.writer.close() # type: ignore
        await self._protocol.wait_for_close() # type: ignore

        self._closed = True
        return self

def create_connection(
    host: str, 
    port: int, 
    *, 
    ssl_context: Optional[Union[ssl.SSLContext, Any]]=None, 
    loop: Optional[asyncio.AbstractEventLoop]=None
):
    client = Client(host, port, ssl_context=ssl_context, loop=loop)
    return client

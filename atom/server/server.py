import asyncio
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
import ssl

from atom import compat

__all__ = [
    'ClientConnection',
    'BaseServer',
    'Server'
]

if sys.platform != 'win32':
    __all__.append('UnixServer')

class Writer:
    def __init__(self, transport: asyncio.Transport) -> None:
        self._transport = transport
        self._waiter = None

    async def _wait_for_drain(self):
        if self._waiter is None:
            return

        try:
            await self._waiter
        finally:
            self._waiter = None

    async def write(self, data: Union[bytearray, bytes]) -> None:
        self._transport.write(data)
        await self._wait_for_drain()

    async def writelines(self, data: List[Union[bytearray, bytes]]) -> None:
        self._transport.writelines(data)
        await self._wait_for_drain()

    def get_extra_info(self, name: str, default: Optional[Any]=None) -> Any:
        return self._transport.get_extra_info(name, default)

    def close(self):
        self._transport.close()

class Reader:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.buffer = bytearray()
        self.loop = loop

        self._waiter = None

    async def _wait_for_data(self, timeout: float=None):
        self._waiter = self.loop.create_future()

        try:
            await asyncio.wait_for(self._waiter, timeout)
        finally:
            self._waiter = None

    def feed_data(self, data: Union[bytearray, bytes]) -> None:
        self.buffer.extend(data)

        if self._waiter:
            self._waiter.set_result(None)

    def feed_eof(self):
        pass

    async def read(self, nbytes: int=None, *, timeout: float=None):
        if not self.buffer:
            await self._wait_for_data(timeout=timeout)

        if not nbytes:
            data = self.buffer
            self.buffer = bytearray()

            return bytes(data)

        if nbytes > len(self.buffer):
            await self._wait_for_data(timeout=timeout)

        data = self.buffer[:nbytes]
        self.buffer = self.buffer[nbytes:]

        return bytes(data)

class ServerProtocol(asyncio.Protocol):
    def __init__(self, loop: asyncio.AbstractEventLoop, max_connections: int) -> None:
        self.loop = loop

        self.readers: Dict[Tuple[str, int], Reader] = {}
        self.writers: Dict[Tuple[str, int], Writer] = {}

        self.pending: asyncio.Queue[asyncio.Transport] = asyncio.Queue(
            maxsize=max_connections
        )

    def __call__(self):
        return self

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport
        peername = transport.get_extra_info('peername')

        try:
            self.pending.put_nowait(transport)
        except asyncio.QueueFull:
            self.transport.close()
            raise ConnectionAbortedError('Too many connections')

        reader = Reader(loop=self.loop)
        writer = Writer(transport)

        self.readers[peername] = reader
        self.writers[peername] = writer

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            raise exc

        peername = self.transport.get_extra_info('peername')

        self.readers.pop(peername, None)
        self.writers.pop(peername, None)

    def get_reader(self, peername: str) -> Optional[Reader]:
        return self.readers.get(peername)

    def get_writer(self, peername: str) -> Optional[Writer]:
        return self.writers.get(peername)

    def data_received(self, data: bytes) -> None:
        peername = self.transport.get_extra_info('peername')
        reader = self.get_reader(peername)

        if not reader:
            return

        reader.feed_data(data)

    def pause_writing(self) -> None:
        peername = self.transport.get_extra_info('peername')
        writer = self.get_writer(peername)

        if not writer:
            return

        writer._waiter = self.loop.create_future()
    
    def resume_writing(self) -> None:
        peername = self.transport.get_extra_info('peername')
        writer = self.get_writer(peername)

        if not writer:
            return

        writer._waiter.set_result(None)

    def eof_received(self) -> None:
        peername = self.transport.get_extra_info('peername')
        reader = self.get_reader(peername)
        if not reader:
            return

        reader.feed_eof()

class ClientConnection:
    def __init__(self, 
                protocol: ServerProtocol, 
                writer: Writer,
                reader: Reader, 
                loop: asyncio.AbstractEventLoop) -> None:
        self._reader = reader
        self._writer = writer
        self._protocol = protocol
        self.loop = loop

    def __repr__(self) -> str:
        return '<ClientConnection peername={0.peername}?'.format(self)

    @property
    def protocol(self):
        return self._protocol

    @property
    def peername(self):
        return self._writer.get_extra_info('peername')

    @property
    def sockname(self):
        return self._writer.get_extra_info('sockname')

    async def receive(self, *, timeout: int=None):
        data = await self._reader.read(timeout=timeout)
        return data

    async def read(self, nbytes: int, *, timeout: int=None):
        data = await self._reader.read(nbytes=nbytes, timeout=timeout)
        return data
    
    async def write(self, data: bytes):
        await self._writer.write(data)
        return len(data)

    async def writelines(self, data: List[bytes]):
        await self._writer.writelines(data)
        return len(b''.join(data))

    async def sendfile(self, 
                    path: Union[str, pathlib.Path], 
                    *, 
                    offset: int=0,
                    count: int=None, 
                    fallback: bool=True) -> int:
        if isinstance(path, pathlib.Path):
            path = path.name

        def read(fn: str):
            with open(fn, 'rb') as f:
                return f.read()

        data = await self.loop.run_in_executor(None, read, path)
        return await self.loop.sendfile(
            transport=self._writer._transport,
            file=data,
            offset=offset,
            count=count,
            fallback=fallback
        )

    def close(self):
        self._writer.close()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.receive()
        except asyncio.TimeoutError:
            raise StopAsyncIteration

def _get_event_loop(loop):
    if loop:
        if not isinstance(loop, asyncio.AbstractEventLoop):
            raise TypeError('Invalid argument type for loop argument')

        return loop

    try:
        return compat.get_running_loop()
    except RuntimeError:
        return compat.get_event_loop()

class BaseServer:
    def __init__(self,
                *,                 
                max_connections: int=None, 
                loop: asyncio.AbstractEventLoop=None, 
                is_ssl: bool=False,
                ssl_context: ssl.SSLContext=None) -> None:
        self.loop = _get_event_loop(loop)
        self.max_connections = max_connections or 254

        self._is_ssl = is_ssl
        self._ssl_context = ssl_context

        if self._is_ssl and not self._ssl_context:
            self._ssl_context = self.create_ssl_context()

        self._waiter = None
        self._closed = False
        self._server: Optional[asyncio.AbstractServer] = None
        self._protocol = ServerProtocol(loop=self.loop, max_connections=self.max_connections)

    def create_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        return context

    def is_ssl(self):
        return self._is_ssl and isinstance(self._ssl_context, ssl.SSLContext)

    def is_serving(self):
        return self._server is not None and isinstance(self._server, asyncio.AbstractServer)

    def is_closed(self):
        return self._closed

    async def __aenter__(self):
        await self.serve()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def serve(self):
        raise NotImplementedError

    async def close(self):
        if self._server:
            await self._server.wait_closed()
            self._server.close()

            if self._waiter:
                self._waiter.set_result(None)

        self._closed = True

    async def accept(self, *, timeout: int=None):
        protocol = self._protocol

        if self._server is None:
            raise RuntimeError('Server not started')

        transport = await asyncio.wait_for(
            fut=protocol.pending.get(),
            timeout=timeout,
        )

        peername = transport.get_extra_info('peername')

        reader = protocol.get_reader(peername)
        writer = protocol.get_writer(peername)

        if not reader:
            return

        if not writer:
            return

        if self.is_ssl():
            transport = await self.loop.start_tls(
                transport=transport,
                protocol=protocol,
                sslcontext=self._ssl_context,
                server_side=True
            )

        return ClientConnection(
            writer=writer,
            protocol=protocol, 
            reader=reader, 
            loop=self.loop
        )

class Server(BaseServer):
    def __init__(self, 
                host: str=None, 
                port: int=None, 
                *,
                max_connections: int=None, 
                loop: asyncio.AbstractEventLoop=None, 
                is_ssl: bool=False,
                ssl_context: ssl.SSLContext=None) -> None:
        self.host = host or '127.0.0.1'
        self.port = port or 8888

        super().__init__(
            max_connections=max_connections,
            loop=loop,
            is_ssl=is_ssl,
            ssl_context=ssl_context
        )

    def __repr__(self) -> str:
        repr = ['<Server']

        for attr in ('host', 'port', 'max_connections', 'is_ssl', 'is_closed', 'is_serving'):
            value = getattr(self, attr)
            if callable(value):
                value = value()

            repr.append(f'{attr}={value!r}')

        return ' '.join(repr) + '>'

    async def serve(self, sock=None):
        if sock:
            self._server = await self.loop.create_server(
                self._protocol,
                sock=sock,
            )
        else:
            self._server = await self.loop.create_server(self._protocol, host=self.host, port=self.port)

        await self._server.start_serving()

        self._waiter = self.loop.create_future()
        return self._waiter

if sys.platform != 'win32':

    class UnixServer(BaseServer):
        def __init__(self, 
                    path: str,
                    *,
                    max_connections: int=None, 
                    loop: asyncio.AbstractEventLoop=None, 
                    is_ssl: bool=None, 
                    ssl_context: ssl.SSLContext=None) -> None:
            self.path = path

            super().__init__(
                max_connections=max_connections, 
                loop=loop, 
                is_ssl=is_ssl, 
                ssl_context=ssl_context
            )

        def __repr__(self) -> str:
            repr = ['<UnixServer']

            for attr in ('path', 'max_connections', 'is_ssl', 'is_closed', 'is_serving'):
                value = getattr(self, attr)
                if callable(value):
                    value = value()

                repr.append(f'{attr}={value!r}')

            return ' '.join(repr) + '>'

        async def serve(self):
            self._server = await self.loop.create_unix_server(self._protocol, self.path)
            await self._server.start_serving()

            self._waiter = self.loop.create_future()
            return self._waiter
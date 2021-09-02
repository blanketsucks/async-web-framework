import asyncio
import pathlib
import io
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
import ssl
import socket

from atom.stream import StreamWriter, StreamReader
from atom import compat, utils

__all__ = [
    'ClientConnection',
    'BaseServer',
    'Server',
    'create_server'
]

if sys.platform != 'win32':
    __all__.append('UnixServer')
    __all__.append('create_unix_server')

class ServerProtocol(asyncio.Protocol):
    def __init__(self, loop: asyncio.AbstractEventLoop, max_connections: int) -> None:
        self.loop = loop

        self.readers: Dict[Tuple[str, int], StreamReader] = {}
        self.writers: Dict[Tuple[str, int], StreamWriter] = {}
        self.waiters: Dict[Tuple[str, int], asyncio.Future[None]] = {}

        self.pending: asyncio.Queue[asyncio.Transport] = asyncio.Queue(
            maxsize=max_connections
        )

    def __call__(self):
        return self

    def connection_made(self, transport: asyncio.Transport) -> None: # type: ignore
        self.transport = transport
        peername = transport.get_extra_info('peername')

        try:
            self.pending.put_nowait(transport)
        except asyncio.QueueFull:
            self.transport.close()
            raise ConnectionAbortedError('Too many connections')

        reader = StreamReader()
        writer = StreamWriter(transport)

        self.readers[peername] = reader
        self.writers[peername] = writer
        self.waiters[peername] = self.loop.create_future()

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            raise exc

        peername = self.transport.get_extra_info('peername')
        waiter = self.waiters.pop(peername, None)

        if waiter:
            waiter.set_result(None)

        self.readers.pop(peername, None)
        self.writers.pop(peername, None)

    def get_reader(self, peername: Tuple[str, int]) -> Optional[StreamReader]:
        return self.readers.get(peername)

    def get_writer(self, peername: Tuple[str, int]) -> Optional[StreamWriter]:
        return self.writers.get(peername)

    def get_waiter(self, peername: Tuple[str, int]) -> Optional[asyncio.Future[None]]:
        return self.waiters.get(peername)

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

        writer._waiter = self.loop.create_future() # type: ignore
    
    def resume_writing(self) -> None:
        peername = self.transport.get_extra_info('peername')
        writer = self.get_writer(peername)

        if not writer:
            return
 
        writer._waiter.set_result(None) # type: ignore

    def eof_received(self) -> None:
        peername = self.transport.get_extra_info('peername')
        reader = self.get_reader(peername)
        if not reader:
            return

        reader.feed_eof()

class ClientConnection:
    def __init__(self, 
                protocol: ServerProtocol, 
                writer: StreamWriter,
                reader: StreamReader, 
                loop: asyncio.AbstractEventLoop) -> None:
        self._reader = reader
        self._writer = writer
        self._protocol = protocol
        self.loop = loop
        self._closed = False

    def __repr__(self) -> str:
        return '<ClientConnection peername={0.peername}>'.format(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    @property
    def protocol(self):
        return self._protocol

    @property
    def peername(self):
        return self._writer.get_extra_info('peername')

    @property
    def sockname(self):
        return self._writer.get_extra_info('sockname')

    def is_closed(self):
        return self._closed

    async def receive(self, nbytes: Optional[int]=None, *, timeout: Optional[int]=None):
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
                    count: Optional[int]=None, 
                    fallback: bool=True) -> int:
        if isinstance(path, pathlib.Path):
            path = path.name

        def read(fn: str):
            with open(fn, 'rb') as f:
                return f.read()

        data = await self.loop.run_in_executor(None, read, path)
        return await self.loop.sendfile(
            transport=self._writer._transport, # type: ignore
            file=io.BytesIO(data),
            offset=offset,
            count=count,
            fallback=fallback
        )

    async def close(self):
        self._writer.close()
        waiter = self.protocol.get_waiter(self.peername)
        if waiter:
            await waiter

        self._closed = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.receive()
        except asyncio.TimeoutError:
            raise StopAsyncIteration

def _get_event_loop(loop: Union[asyncio.AbstractEventLoop, Any]):
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
                max_connections: Optional[int]=None, 
                loop: Optional[asyncio.AbstractEventLoop]=None, 
                is_ssl: Optional[bool]=False,
                ssl_context: Optional[ssl.SSLContext]=None) -> None:
        self.loop = _get_event_loop(loop)
        self.max_connections = max_connections or 254

        self._is_ssl = is_ssl
        self._ssl_context = ssl_context

        if self._is_ssl and not self._ssl_context:
            self._ssl_context = self.create_ssl_context()

        self._waiter: Optional['asyncio.Future[None]'] = None
        self._closed = False
        self._server: Optional[asyncio.AbstractServer] = None
        self._protocol = ServerProtocol(loop=self.loop, max_connections=self.max_connections)

    def create_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        return context

    def is_ssl(self):
        return self._is_ssl and isinstance(self._ssl_context, ssl.SSLContext)

    def is_serving(self):
        return self._server is not None

    def is_closed(self):
        return self._closed

    async def __aenter__(self):
        await self.serve()
        return self

    async def __aexit__(self, *exc: Any):
        await self.close()

    async def serve(self) -> 'asyncio.Future[None]':
        raise NotImplementedError

    async def close(self):
        if self._server:
            await self._server.wait_closed()
            self._server.close()

            if self._waiter:
                self._waiter.set_result(None)

        self._closed = True

    async def accept(self, *, timeout: Optional[int]=None) -> Optional[ClientConnection]:
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

        if self.is_ssl() and self._ssl_context is not None:
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
                host: Optional[str]=None, 
                port: Optional[int]=None, 
                *,
                ipv6: bool=False,
                max_connections: Optional[int]=None, 
                loop: Optional[asyncio.AbstractEventLoop]=None, 
                is_ssl: Optional[bool]=False,
                ssl_context: Optional[ssl.SSLContext]=None) -> None:
        if ipv6:
            if not utils.has_ipv6():
                raise RuntimeError('IPv6 is not supported')

        self.host = utils.validate_ip(host, ipv6=ipv6)
        self.port = port or 8888
        self.ipv6 = ipv6

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

    async def serve(self, sock: Optional[socket.socket]=None):
        if sock:
            self._server = server = await self.loop.create_server(
                self._protocol,
                sock=sock,
            )
        else:
            self._server = server = await self.loop.create_server(
                self._protocol, 
                host=self.host, 
                port=self.port,
                family=socket.AF_INET6 if self.ipv6 else socket.AF_INET,
            )

        await server.start_serving()

        self._waiter = waiter = self.loop.create_future()
        return waiter

def create_server(
    host: Optional[str]=None, 
    port: Optional[int]=None, 
    *,
    max_connections: Optional[int]=None, 
    loop: Optional[asyncio.AbstractEventLoop]=None, 
    is_ssl: bool=False,
    ssl_context: Optional[ssl.SSLContext]=None
):
    return Server(
        host=host,
        port=port,
        max_connections=max_connections,
        loop=loop,
        is_ssl=is_ssl,
        ssl_context=ssl_context
    )

if sys.platform != 'win32':

    class UnixServer(BaseServer):
        def __init__(self, 
                    path: str,
                    *,
                    max_connections: Optional[int]=None, 
                    loop: Optional[asyncio.AbstractEventLoop]=None, 
                    is_ssl: bool=None, 
                    ssl_context: Optional[ssl.SSLContext]=None) -> None:
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
            self._server = server = await self.loop.create_unix_server(self._protocol, self.path)
            await server.start_serving()

            self._waiter = self.loop.create_future()
            return self._waiter

    def create_unix_server(
        path: str,
        *,
        max_connections: Optional[int]=None, 
        loop: Optional[asyncio.AbstractEventLoop]=None, 
        is_ssl: bool=None, 
        ssl_context: Optional[ssl.SSLContext]=None
    ):
        return UnixServer(
            path=path,
            max_connections=max_connections,
            loop=loop,
            is_ssl=is_ssl,
            ssl_context=ssl_context
        )


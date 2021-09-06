import asyncio
import pathlib
import io
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
import ssl
import socket

from railway.stream import StreamWriter, StreamReader
from railway import compat, utils

__all__ = [
    'ClientConnection',
    'BaseServer',
    'TCPServer',
    'create_server'
]

if sys.platform != 'win32':
    __all__.append('UnixServer')
    __all__.append('create_unix_server')

class ServerProtocol(asyncio.Protocol): 
    """
    A subclass of `asyncio.Protocol` that implements the server side of a connection.

    Attributes:
        loop: The event loop.
        pending: An `asyncio.Queue` of pending connections.
        readers: A mapping of peername to `StreamReader` objects.
        writers: A mapping of peername to `StreamWriter` objects.
        waiters: A mapping of peername to `asyncio.Future` objects.
    """
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

        reader = StreamReader(self.loop)
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

    def get_waiter(self, peername: Tuple[str, int]) -> Optional['asyncio.Future[None]']:
        return self.waiters.get(peername)

    def data_received(self, data: bytes) -> None:
        peername = self.transport.get_extra_info('peername')
        reader = self.get_reader(peername)

        if not reader:
            reader = StreamReader(self.loop)
            self.readers[peername] = reader

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
            writer = StreamWriter(self.transport)
            self.writers[peername] = writer
 
        writer._waiter.set_result(None) # type: ignore

    def eof_received(self) -> None:
        peername = self.transport.get_extra_info('peername')
        reader = self.get_reader(peername)

        if not reader:
            return

        reader.feed_eof()

class ClientConnection:
    """
    A class representing a client connection to a server.
    This class should not be instantiated directly by the user.
    
    Attributes:
        loop: The event loop used.

    """
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
    def protocol(self) -> ServerProtocol:
        """
        Returns:
            The protocol used by the connection.
        """
        return self._protocol

    @property
    def peername(self) -> Tuple[str, int]:
        """
        Returns:
            The peername of the connection.
        """
        return self._writer.get_extra_info('peername')

    @property
    def sockname(self) -> Tuple[str, int]:
        """
        Returns:
            The sockname of the connection.
        """
        return self._writer.get_extra_info('sockname')

    def is_closed(self) -> bool:
        """
        Returns:
            True if the connection is closed.
        """
        return self._closed

    async def receive(self, nbytes: Optional[int]=None, *, timeout: Optional[int]=None) -> bytes:
        """
        Receives data from the connection.

        Args:
            nbytes: The number of bytes to receive..
            timeout: The maximum time to wait for the data to be received.

        Returns:
            The received data.

        Raises:
            asyncio.TimeoutError: If the data could not be received in time.
        """
        data = await self._reader.read(nbytes=nbytes, timeout=timeout)
        return data
    
    async def write(self, data: bytes) -> int:
        """
        Writes data to the connection.

        Args:
            data: The data to write.

        Returns:
            The number of bytes written.

        """
        await self._writer.write(data)
        return len(data)

    async def writelines(self, data: List[bytes]) -> int:
        """
        Writes a list of data to the connection.

        Args:
            data: The data to write.

        Returns:
            The number of bytes written.
        """
        await self._writer.writelines(data)
        return len(b''.join(data))

    async def sendfile(self, 
                    path: Union[str, pathlib.Path], 
                    *, 
                    offset: int=0,
                    count: Optional[int]=None, 
                    fallback: bool=True) -> int:
        """
        Sends a file to the client.

        Args:
            path: The path to the file to send.
            offset: The offset in the file to start sending from.
            count: The number of bytes to send.
            fallback: Whether to fallback to sending the file in chunks if the file is too large to fit in one message.
        
        Returns:
            The number of bytes sent.
        """
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
        """
        Closes the connection.
        """
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
    """
    A base server class, All server classes should inherit from this class.

    Attributes:
        loop: The event loop used.
        max_connections: The maximum number of connections to keep pending.
    """
    def __init__(self,
                *,                 
                max_connections: Optional[int]=None, 
                loop: Optional[asyncio.AbstractEventLoop]=None, 
                is_ssl: Optional[bool]=False,
                ssl_context: Optional[ssl.SSLContext]=None) -> None:
        """
        Args:
            max_connections: The maximum number of connections to keep pending.
            loop: The event loop used.
            is_ssl: Whether to use SSL.
            ssl_context: The SSL context to use.
        """
        self.loop: asyncio.AbstractEventLoop = _get_event_loop(loop)
        self.max_connections: int = max_connections or 254

        self._is_ssl = is_ssl
        self._ssl_context = ssl_context

        if self._is_ssl and not self._ssl_context:
            self._ssl_context = self.create_ssl_context()

        self._waiter: Optional['asyncio.Future[None]'] = None
        self._closed = False
        self._server: Optional[asyncio.AbstractServer] = None
        self._protocol = ServerProtocol(loop=self.loop, max_connections=self.max_connections)

    def create_ssl_context(self) -> ssl.SSLContext:
        """
        Creates a default SSL context.

        Returns:
            The SSL context.
        """
        context = ssl.create_default_context()
        return context

    def is_ssl(self) -> bool:
        """
        Returns:
            True if the server is using SSL.
        """
        return self._is_ssl and isinstance(self._ssl_context, ssl.SSLContext)

    def is_serving(self) -> bool:
        """
        Returns:
            True if the server is serving.
        """
        return self._server is not None

    def is_closed(self) -> bool:
        """
        Returns:
            True if the server is closed.
        """
        return self._closed

    async def __aenter__(self):
        await self.serve()
        return self

    async def __aexit__(self, *exc: Any):
        await self.close()

    async def serve(self) -> 'asyncio.Future[None]':
        raise NotImplementedError

    async def close(self):
        """
        Closes the server.
        """
        if self._server:
            await self._server.wait_closed()
            self._server.close()

            if self._waiter:
                self._waiter.set_result(None)

        self._closed = True

    async def accept(self, *, timeout: Optional[int]=None) -> Optional[ClientConnection]:
        """
        Accepts an incoming connection.

        Args:
            timeout: The timeout to wait for a connection.

        Returns:
            The client connection if one is available.

        Raises:
            asyncio.TimeoutError: If the timeout is reached.
        """
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

        # if self.is_ssl() and self._ssl_context is not None:
        #     transport = await self.loop.start_tls(
        #         transport=transport,
        #         protocol=protocol,
        #         sslcontext=self._ssl_context,
        #         server_side=True
        #     )

        # print('?')
        return ClientConnection(
            writer=writer,
            protocol=protocol, 
            reader=reader, 
            loop=self.loop
        )

class TCPServer(BaseServer):
    """
    A TCP server

    Attributes:
        loop: The event loop used.
        max_connections: The maximum number of connections to keep pending.
        host: The host to listen on.
        port: The port to listen on.
        ipv6: Whether to use IPv6.
    """
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

        self.host: str = host
        self.port: int = port or 8080
        self.ipv6: bool = ipv6

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

    async def serve(self, sock: Optional[socket.socket]=None) -> 'asyncio.Future[None]':
        """
        Starts the server.

        Args:
            sock: The socket to use.

        Returns:
            A future that will be resolved when the server is closed.
        """
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
    ipv6: bool=False,
    max_connections: Optional[int]=None, 
    loop: Optional[asyncio.AbstractEventLoop]=None, 
    is_ssl: bool=False,
    ssl_context: Optional[ssl.SSLContext]=None
):
    """
    A helper function to create a server.

    Args:
        host: The host to listen on.
        port: The port to listen on.
        ipv6: Whether to use IPv6.
        max_connections: The maximum number of connections to keep pending.
        loop: The event loop used.
        is_ssl: Whether to use SSL.
        ssl_context: The SSL context to use.
    """
    return TCPServer(
        host=host,
        port=port,
        ipv6=ipv6,
        max_connections=max_connections,
        loop=loop,
        is_ssl=is_ssl,
        ssl_context=ssl_context
    )

if sys.platform != 'win32':

    class UnixServer(BaseServer):
        """
        A Unix server

        Attributes:
            loop: The event loop used.
            max_connections: The maximum number of connections to keep pending.
            path: The path of the socket to listen on.
        """
        def __init__(self, 
                    path: str,
                    *,
                    max_connections: Optional[int]=None, 
                    loop: Optional[asyncio.AbstractEventLoop]=None, 
                    is_ssl: bool=None, 
                    ssl_context: Optional[ssl.SSLContext]=None) -> None:
            """
            Args:
                path: The path of the socket to listen on.
                max_connections: The maximum number of connections to keep pending.
                loop: The event loop used.
                is_ssl: Whether to use SSL.
                ssl_context: The SSL context to use.
            """
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
            """
            Starts the UNIX server.

            Returns:
                A future that will be resolved when the server is closed.
            """
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
        """
        A helper function to create a UNIX server.

        Args:
            path: The path of the socket to listen on.
            max_connections: The maximum number of connections to keep pending.
            loop: The event loop used.
            is_ssl: Whether to use SSL.
            ssl_context: The SSL context to use.
        """
        return UnixServer(
            path=path,
            max_connections=max_connections,
            loop=loop,
            is_ssl=is_ssl,
            ssl_context=ssl_context
        )

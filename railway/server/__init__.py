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
import asyncio
import pathlib
import io
import sys
from typing import Any, List, Optional, Tuple, Union, cast
import ssl
import socket

from railway.streams import StreamTransport
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

    Attributes
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop.
    pending: :class:`asyncio.Queue`
        Pending connections. If you passed in ``max_pending_connections`` to the :class:`~railway.Application`,
        the queue's max size is set to that value.
    transports: :class:`dict`
        A dictionary of :class:`~railway.streams.StreamTransport` objects.
    waiters: :class:`dict`
        A dictionary of :class:`~asyncio.Future` objects.
    """
    def __init__(self, loop: asyncio.AbstractEventLoop, max_connections: Optional[int]) -> None:
        self.loop = loop
        self.pending: asyncio.Queue[Tuple[StreamTransport, 'asyncio.Future[None]']] = asyncio.Queue(
            maxsize=0 if max_connections is None else max_connections
        )

    def __call__(self):
        return self

    def connection_made(self, transport: asyncio.Transport) -> None: # type: ignore
        self.waiter = self.loop.create_future()
        self.transport = StreamTransport(transport, self.waiter)

        try:
            self.pending.put_nowait((self.transport, self.waiter))
        except asyncio.QueueFull:
            self.transport.abort()
            return

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            raise exc

        try:
            self.waiter.set_result(None)
        except asyncio.InvalidStateError:
            pass

    def data_received(self, data: bytes) -> None:
        self.transport.feed_data(data)

    def pause_writing(self) -> None:
        self.transport.pause_writing()
    
    def resume_writing(self) -> None:
        self.transport.resume_writing()

    def eof_received(self) -> None:
        self.transport.feed_eof()

class ClientConnection:
    """
    A class representing a client connection to a server.
    This class should not be instantiated directly by the user.
    
    Attributes
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    """
    def __init__(self, 
                protocol: ServerProtocol, 
                transport: StreamTransport,
                loop: asyncio.AbstractEventLoop
                ) -> None:
        self._transport = transport
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
        The protocol used by the connection.
        """
        return self._protocol

    @property
    def peername(self) -> Tuple[str, int]:
        """
        The peername of the connection.
        """
        return self._transport.get_extra_info('peername')

    @property
    def sockname(self) -> Tuple[str, int]:
        """
        The sockname of the connection.
        """
        return self._transport.get_extra_info('sockname')

    def is_closed(self) -> bool:
        """
        True if the connection is closed.
        """
        return self._closed

    async def receive(self, nbytes: Optional[int]=None, *, timeout: Optional[float]=None) -> bytes:
        """
        Receives data from the connection.

        Parameters
        ----------
        nbytes: :class:`int`
            The number of bytes to receive..
        timeout: :class:`float`
            The maximum time to wait for the data to be received.

        Raises
        ------
        asyncio.TimeoutError: If the data could not be received in time.
        """
        data = await self._transport.receive(nbytes=nbytes, timeout=timeout)
        return data
    
    async def write(self, data: bytes) -> int:
        """
        Writes data to the connection.

        Parameters
        ----------
        data: :class:`bytes`
            The data to write.
        """
        await self._transport.write(data)
        return len(data)

    async def writelines(self, data: List[bytes]) -> int:
        """
        Writes a list of data to the connection.

        Parameters
        ----------
        data: :class:`List[bytes]`
            The data to write.
        """
        await self._transport.writelines(data)
        return len(b''.join(data))

    async def sendfile(self, 
                    path: Union[str, pathlib.Path], 
                    *, 
                    offset: int=0,
                    count: Optional[int]=None, 
                    fallback: bool=True) -> int:
        """
        Sends a file to the client.

        Parameters
        ----------
        path: Union[:class:`str`, :class:`pathlib.Path`]
            The path to the file to send.
        offset: :class:`int`
            The offset in the file to start sending from.
        count: :class:`int`
            The number of bytes to send.
        fallback: :class:`bool`
            Whether to fallback to sending the file in chunks if the file is too large to fit in one message.
        """
        if isinstance(path, pathlib.Path):
            path = path.name

        def read(fn: str):
            with open(fn, 'rb') as f:
                return f.read()

        data = await self.loop.run_in_executor(None, read, path)
        return await self.loop.sendfile(
            transport=self._transport._transport, # type: ignore
            file=io.BytesIO(data),
            offset=offset,
            count=count,
            fallback=fallback
        )

    async def close(self):
        """
        Closes the connection.
        """
        await self._transport.close()
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

    Parameters
    ----------
    max_connections: :class:`int`
        The maximum number of connections to keep pending.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    is_ssl: :class:`bool`
        Whether to use SSL.
    ssl_context: :class:`ssl.SSLContext`
        The SSL context to use.

    Attributes
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    max_connections: :class:`int`
        The maximum number of connections to keep pending.
    """
    def __init__(self,
                *,                 
                max_connections: Optional[int]=None, 
                loop: Optional[asyncio.AbstractEventLoop]=None, 
                is_ssl: bool=False,
                ssl_context: Optional[ssl.SSLContext]=None) -> None:
        self.loop: asyncio.AbstractEventLoop = _get_event_loop(loop)
        self.max_connections: Optional[int] = max_connections

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
        """
        context = ssl.create_default_context()
        return context

    def is_ssl(self) -> bool:
        """
        True if the server is using SSL.
        """
        return self._is_ssl and isinstance(self._ssl_context, ssl.SSLContext)

    def is_serving(self) -> bool:
        """
        True if the server is serving.
        """
        return self._server is not None

    def is_closed(self) -> bool:
        """
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
            self._server.close()
            await self._server.wait_closed()

            if self._waiter:
                self._waiter.set_result(None)

        self._closed = True

    async def accept(self, *, timeout: Optional[int]=None) -> ClientConnection:
        """
        Accepts an incoming connection.

        Parameters
        ----------
        timeout: :class:`int`
            The timeout to wait for a connection.

        Raises
        ------
        asyncio.TimeoutError: If the timeout is reached.
        """
        protocol = self._protocol

        if self._server is None:
            raise RuntimeError('Server not started')

        transport, future = await asyncio.wait_for(
            fut=protocol.pending.get(),
            timeout=timeout,
        )

        if self.is_ssl() and self._ssl_context is not None:
            trans = await self.loop.start_tls(
                transport=transport._transport, # type: ignore
                protocol=protocol,
                sslcontext=self._ssl_context,
                server_side=True
            )

            trans = cast(asyncio.Transport, trans)
            transport = StreamTransport(trans, future)

        return ClientConnection(
            protocol=protocol, 
            transport=transport,
            loop=self.loop,
        )

class TCPServer(BaseServer):
    """
    A TCP server

    Parameters
    ----------
    host: :class:`str`
        The host to listen on.
    port: :class:`int`
        The port to listen on.
    max_connections: :class:`int`
        The maximum number of connections to keep pending.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    is_ssl: :class:`bool`
        Whether to use SSL.
    ssl_context: :class:`ssl.SSLContext`
        The SSL context to use.

    Attributes
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    max_connections: :class:`int`
        The maximum number of connections to keep pending.
    host: :class:`str`
        The host to listen on.
    port: :class:`int`
        The port to listen on.
    ipv6: :class:`bool`
        Whether to use IPv6.
    """
    def __init__(self, 
                host: Optional[str]=None, 
                port: Optional[int]=None, 
                *,
                ipv6: bool=False,
                max_connections: Optional[int]=None, 
                loop: Optional[asyncio.AbstractEventLoop]=None, 
                is_ssl: bool=False,
                ssl_context: Optional[ssl.SSLContext]=None) -> None:
        if ipv6:
            if not utils.has_ipv6():
                raise RuntimeError('IPv6 is not supported')

        self.host = host
        self.port = port or 8080
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

    async def serve(self, sock: Optional[socket.socket]=None) -> 'asyncio.Future[None]':
        """
        Starts the server.

        Parameters
        ----------
        sock: :class:`socket.socket`
            The socket to use.
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
                ssl=self._ssl_context,
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
    A helper function to create TCP a server.

    Parameters
    ----------
    host: :class:`str`
        The host to listen on.
    port: :class:`int`
        The port to listen on.
    max_connections: :class:`int`
        The maximum number of connections to keep pending.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    is_ssl: :class:`bool`
        Whether to use SSL.
    ssl_context: :class:`ssl.SSLContext`
        The SSL context to use.

    Example
    ---------
    .. code-block:: python3

        server = await create_server(*args, **kwargs)

        # or, alternatively

        async with create_server(*args, **kwargs) as server:
            ...

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

class UnixServer(BaseServer):
    """
    A Unix server

    Attributes
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    max_connections: :class:`int`
        The maximum number of connections to keep pending.
    path: :class:`str`
        The path of the socket to listen on.

    Parameters
    ------------
    path: :class:`str`
        The path of the socket to listen on.
    max_connections: :class:`int`
        The maximum number of connections to keep pending.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    is_ssl: :class:`bool`
        Whether to use SSL.
    ssl_context: :class:`ssl.SSLContext`
        The SSL context to use.
    """
    def __init__(self, 
                path: str,
                *,
                max_connections: Optional[int]=None, 
                loop: Optional[asyncio.AbstractEventLoop]=None, 
                is_ssl: bool=False, 
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
        """
        Starts the UNIX server.
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
    is_ssl: bool=False, 
    ssl_context: Optional[ssl.SSLContext]=None
):
    """
    A helper function to create a UNIX server.

    Parameters
    ------------
    path: :class:`str`
        The path of the socket to listen on.
    max_connections: :class:`int`
        The maximum number of connections to keep pending.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    is_ssl: :class:`bool`
        Whether to use SSL.
    ssl_context: :class:`ssl.SSLContext`
        The SSL context to use.
    """
    return UnixServer(
        path=path,
        max_connections=max_connections,
        loop=loop,
        is_ssl=is_ssl,
        ssl_context=ssl_context
    )

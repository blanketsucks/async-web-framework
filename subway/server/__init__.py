from typing import Any, Optional, Union
import asyncio
import sys
import ssl
import socket

from subway import compat
from subway.streams import StreamReader, StreamWriter, start_server, start_unix_server

__all__ = [
    'BaseServer',
    'TCPServer',
]

if sys.platform != 'win32':
    __all__.append('UnixServer')

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
    """
    def __init__(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        is_ssl: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None
    ) -> None:
        self.loop: asyncio.AbstractEventLoop = _get_event_loop(loop)

        self._is_ssl = is_ssl
        self._ssl_context = ssl_context

        if self._is_ssl and not self._ssl_context:
            self._ssl_context = self.create_ssl_context()

        self._closed = False
        self._server: Optional[asyncio.AbstractServer] = None

    @staticmethod
    def create_ssl_context() -> ssl.SSLContext:
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

    def __await__(self):
        return self.serve().__await__()

    async def __aenter__(self):
        await self.serve()
        return self

    async def __aexit__(self, *exc: Any):
        await self.close()

    async def serve(self, *, sock: Optional[socket.socket] = None) -> Any:
        raise NotImplementedError

    async def close(self):
        """
        Closes the server.
        """
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        self._server = None
        self._closed = True

    async def on_transport_connect(self, reader: StreamReader, writer: StreamWriter) -> None:
        """
        A callback called on a new connection.
        To be subclassed and overriden by users.

        Parameters
        ----------
        writer: :class:`~subway.streams.StreamWriter`
            The writer of the connection.
        reader: :class:`~subway.streams.StreamReader`
            The reader of the connection.
        """

class TCPServer(BaseServer):
    """
    A TCP server

    Parameters
    ----------
    host: Optional[:class:`str`]
        The host to listen on.
    port: Optional[:class:`int`]
        The port to listen on.
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
    host: :class:`str`
        The host to listen on.
    port: :class:`int`
        The port to listen on.
    """
    def __init__(
        self, 
        host: Optional[str] = None,
        port: Optional[int] = None,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        is_ssl: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None
    ) -> None:
        self.host = host
        self.port = port

        super().__init__(
            loop=loop,
            is_ssl=is_ssl,
            ssl_context=ssl_context
        )

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} host={self.host!r} port={self.port!r}>'

    async def serve(self, *, sock: Optional[socket.socket] = None) -> None:
        """
        Starts the server.

        Parameters
        ----------
        sock: :class:`socket.socket`
            The socket to use.
        """
        if sock:
            if self.host is not None or self.port is not None:
                raise ValueError('Cannot specify both sock and host/port')

            if sock.type is not socket.SOCK_STREAM:
                raise TypeError('Invalid argument type for sock argument')

        self._server = server = await start_server(
            host=self.host,
            port=self.port,
            connection_callback=self.on_transport_connect,
            sock=sock,
            ssl=self._ssl_context,
            start_serving=False,
        )

        await server.start_serving()

class UnixServer(BaseServer):
    """
    A Unix server

    Attributes
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    path: :class:`str`
        The path of the socket to listen on.

    Parameters
    ------------
    path: :class:`str`
        The path of the socket to listen on.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used.
    is_ssl: :class:`bool`
        Whether to use SSL.
    ssl_context: :class:`ssl.SSLContext`
        The SSL context to use.
    """
    def __init__(
        self,
        path: Optional[str] = None,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        is_ssl: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None
    ) -> None:
        self.path = path

        super().__init__(
            loop=loop, 
            is_ssl=is_ssl, 
            ssl_context=ssl_context
        )

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} path={self.path!r}>'

    async def serve(self, *, sock: Optional[socket.socket] = None) -> None:
        """
        Starts the UNIX server.
        """
        if sock:
            if self.path:
                raise ValueError('path and sock cannot be specified together')

            if sock.type is not socket.SOCK_STREAM:
                raise ValueError('sock must be of type SOCK_STREAM')

            if sock.family is not socket.AF_UNIX:
                raise ValueError('sock must be of family AF_UNIX')

        self._server = server = await start_unix_server(
            path=self.path,
            connection_callback=self.on_transport_connect,
            sock=sock,
        )
        await server.start_serving()



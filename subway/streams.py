from typing import Callable, List, Literal, Tuple, Optional, Any, overload, TypedDict, Union
import asyncio
import socket
import ssl

from . import compat, utils
from .types import BytesLike, Coro
from .errors import PartialRead

class Peercert(TypedDict, total=False):
    subject: Tuple[Tuple[Tuple[str, str]]]
    issuer: Tuple[Tuple[Tuple[str, str]]]
    version: int
    serialNumber: int
    notBefore: str
    notAfter: str
    subjectAltName: Tuple[Tuple[str, str], ...]
    OCSP: Tuple[Tuple[str, str]]
    caIssuers: Tuple[str, ...]
    crlDistributionPoints: Tuple[str, ...]


__all__ = (
    'StreamWriter',
    'StreamReader',
    'StreamProtocol',
    'open_connection',
    'start_server',
    'start_unix_server'
)

class StreamWriter:
    """
    Parameters
    -----------
    transport: :class:`asyncio.Transport`
        The transport to use.
    """
    def __init__(self, transport: asyncio.Transport, close_waiter: asyncio.Future[None]) -> None:
        self._transport = transport
        self._close_waiter = close_waiter
        self._waiter: 'Optional[asyncio.Future[None]]' = None
        self._loop = compat.get_running_loop()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any):
        self.close()
        await self.wait_closed()

    @property
    def transport(self) -> asyncio.Transport:
        """
        The transport used by this writer
        """
        return self._transport

    async def _wait_for_drain(self, timeout: float = None) -> None:
        if self._waiter is None:
            return

        try:
            await asyncio.wait_for(self._waiter, timeout)
        finally:
            self._waiter = None

    def pause_writing(self):
        """
        Creates a future that is resolved when :meth:~`.StreamWriter.resume_writing` is called.
        This is supposed to be called when :meth:`asyncio.Protocol.pause_writing` is called.
        """
        if not self._waiter:
            self._waiter = self._loop.create_future()

    def resume_writing(self):
        """
        Sets the future that was created by :meth:~`.StreamWriter.pause_writing` to be resolved.
        This is supposed to be called when :meth:`asyncio.Protocol.resume_writing` is called.
        """
        if self._waiter:
            self._waiter.set_result(None)

    @overload
    def write(self, data: BytesLike) -> None:
        ...
    @overload
    def write(self, data: BytesLike, *, drain: Literal[True]) -> Coro[None]:
        ...
    @overload
    def write(self, data: BytesLike, *, drain: Literal[False]) -> None:
        ...
    def write(self, data: BytesLike, *, drain: bool = False) -> Any:
        """
        Writes data to the transport.

        Parameters
        ----------
        data: Union[:class:`bytearray`, :class:`bytes`]
            data to write.
        drain: :class:`bool`
            Whether to wait until all data has been written.
        """
        self._transport.write(data)
        if drain:
            return self.drain()

    @overload
    def writelines(self, data: List[BytesLike]) -> None:
        ...
    @overload
    def writelines(self, data: List[BytesLike], *, drain: Literal[True]) -> Coro[None]:
        ...
    @overload
    def writelines(self, data: List[BytesLike], *, drain: Literal[False]) -> None:
        ...
    def writelines(self, data: List[BytesLike], *, drain: bool = False) -> Any:
        """
        Writes a list of data to the transport.

        Parameters
        ----------
        data: List[Union[:class:`bytearray`, :class:`bytes`]]
            list of data to write.
        drain: :class:`bool`
            Whether to wait until all data has been written.
        """
        self._transport.writelines(data)
        if drain:
            return self.drain()

    def write_eof(self):
        """
        Writes EOF to the transport.
        """
        self._transport.write_eof()

    def set_write_buffer_limits(self, high: Optional[int] = None, low: Optional[int] = None) -> None:
        """
        Sets the high-water and low-water limits for write flow control.

        Parameters
        ------------
        high: Optional[:class:`int`]
            The high-water limit.
        low: Optional[:class:`int`]
            The low-water limit.
        """
        self._transport.set_write_buffer_limits(high, low)

    def get_write_buffer_size(self) -> int:
        """
        Gets the size of the write buffer.
        """
        return self._transport.get_write_buffer_size()

    async def drain(self, *, timeout: Optional[float] = None):
        """
        Waits until all data has been written.
        """
        if self.transport.is_closing():
            await asyncio.sleep(0)

        await self._wait_for_drain(timeout)

    @overload
    def get_extra_info(self, name: Literal['peername', 'sockname']) -> Tuple[str, int]: ...
    @overload
    def get_extra_info(self, name: Literal['socket']) -> socket.socket: ...
    @overload
    def get_extra_info(self, name: Literal['compression']) -> Optional[str]: ...
    @overload
    def get_extra_info(self, name: Literal['cipher']) -> Optional[Tuple[str, str, int]]: ...
    @overload
    def get_extra_info(self, name: Literal['peercert']) -> Optional[Peercert]: ...
    @overload
    def get_extra_info(self, name: Literal['sslcontext']) -> Optional[ssl.SSLContext]: ...
    @overload
    def get_extra_info(self, name: Literal['ssl_object']) -> Optional[Union[ssl.SSLObject, ssl.SSLSocket]]: ...
    def get_extra_info(self, name: str) -> Any:
        """
        Gets extra info about the transport.

        Parameters
        ----------
        name: :class:`str`
            The name of the extra info.
        """
        return self._transport.get_extra_info(name)

    def set_protocol(self, protocol: asyncio.BaseProtocol) -> None:
        """
        Sets the protocol used by the transport.

        Parameters
        ----------
        protocol: :class:`asyncio.BaseProtocol`
            The protocol to use.
        """
        self._transport.set_protocol(protocol)

    def get_protocol(self) -> asyncio.BaseProtocol:
        """
        Gets the protocol used by the transport.
        """
        return self._transport.get_protocol()

    def close(self):
        """
        Closes the transport.
        """
        self._transport.close()

    async def wait_closed(self) -> None:
        """
        Waits until the transport is closed.
        """
        await self._close_waiter


class StreamReader:
    """
    Attributes
    ----------
    buffer: :class:`bytearray`
        A bytearray containing the data.
    loop: :class:`asyncio.AbstractEventLoop`
        A reference to the event loop.
    """

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.buffer: bytearray = bytearray()
        self.loop: asyncio.AbstractEventLoop = loop or compat.get_running_loop()

        self._waiter: Optional[asyncio.Future[None]] = None
        self._eof = False

    def __aiter__(self):
        return self
    
    async def __anext__(self):
        data = await self.readline(wait=False)
        if not data:
            raise StopAsyncIteration

        return data

    async def _wait_for_data(self, timeout: Optional[float] = None):
        if self.at_eof():
            raise RuntimeError('Cannot wait for data after EOF')

        if self._waiter is not None:
            raise RuntimeError('Already waiting for data')

        self._waiter = self.loop.create_future()

        try:
            await asyncio.wait_for(self._waiter, timeout)
        finally:
            self._waiter = None

    def at_eof(self) -> bool:
        """
        Returns whether the reader has reached EOF.
        """
        return self._eof

    def reset(self) -> bytes:
        """
        Resets the reader's buffer.
        """
        data = self.buffer
        self.buffer = bytearray()

        return bytes(data)

    def feed_data(self, data: BytesLike) -> None:
        """
        Feeds the data to the reader.

        Parameters
        ----------
        data: Union[:class:`bytearray`, :class:`bytes`]
            data to be fed.
        """
        if self._eof:
            raise RuntimeError('Cannot feed data after EOF')

        self.buffer.extend(data)

        if self._waiter:
            try:
                self._waiter.set_result(None)
            except asyncio.InvalidStateError:
                pass
            
    def feed_eof(self):
        """
        Feeds EOF to the reader.
        """
        if self._waiter:
            try:
                self._waiter.set_result(None)
            except asyncio.InvalidStateError:
                pass

        self._eof = True

    async def read(
        self, 
        nbytes: Optional[int] = None, 
        *, 
        timeout: Optional[float] = None,
        wait: bool = True
    ) -> bytes:
        """
        Reads ``nbytes`` off the stream. If ``nbytes`` is not provided, reads the whole stream.

        Parameters
        ----------
        nbytes: :class:`int`
            Number of bytes to read.
        timeout: Optional[:class:`float`]
            Timeout to wait for the read to complete.
        wait: :class:`bool`
            Whether to wait for data to be available.

        Raises
        ------
        asyncio.TimeoutError: If the timeout expires.
        """
        if not self.buffer:
            if wait:
                await self._wait_for_data(timeout=timeout)
            else:
                return b''

        if not nbytes:
            return self.reset()

        while nbytes > len(self.buffer):
            if self.at_eof():
                buffer = self.reset()
                raise PartialRead(buffer, nbytes)

            await self._wait_for_data(timeout=timeout)

        data = self.buffer[:nbytes]
        self.buffer = self.buffer[nbytes:]

        return bytes(data)

    async def readuntil(
        self, 
        delimiter: BytesLike, 
        *, 
        timeout: Optional[float] = None,
        wait: bool = True,
        include: bool = False
    ) -> bytes:
        """
        Reads until the delimiter is found.

        Parameters
        ----------
        delimiter: Union[:class:`bytearray`, :class:`bytes`]
            The delimiter to read until.
        timeout: Optional[:class:`float`]
            Timeout to wait for the read to complete.
        wait: :class:`bool`
            Whether to wait for data to be available.
        include: :class:`bool`
            Whether to include the delimiter in the returned data.

        Raises
        ------
        asyncio.TimeoutError: If the timeout expires.
        """
        if not self.buffer:
            if wait:
                await self._wait_for_data(timeout=timeout)
            else:
                return b''

        pos = self.buffer.find(delimiter)
        while pos == -1:
            if self.at_eof():
                buffer = self.reset()
                raise PartialRead(buffer, None)

            await self._wait_for_data(timeout=timeout)
            pos = self.buffer.find(delimiter)

        if include:
            data = self.buffer[:pos + len(delimiter)]
        else:
            data = self.buffer[:pos]

        self.buffer = self.buffer[pos + len(delimiter):]
        return bytes(data)

    async def readline(
        self, 
        *, 
        timeout: Optional[float] = None,
        wait: bool = True,
        include: bool = False
    ) -> bytes:
        """
        Reads a line off the stream.

        Parameters
        ----------
        timeout: Optional[:class:`float`]
            Timeout to wait for the read to complete.
        wait: :class:`bool`
            Whether to wait for data to be available.
        include: :class:`bool`
            Whether to include the delimiter in the returned data.

        Raises
        ------
        asyncio.TimeoutError: If the timeout expires.
        """
        try:
            return await self.readuntil(b'\n', timeout=timeout, wait=wait, include=include)
        except PartialRead as e:
            return e.partial

    async def readlines(
        self, 
        hint: Optional[int] = None, 
        *, 
        timeout: Optional[float] = None,
        wait: bool = False
    ) -> List[bytes]:
        """
        Reads all lines off the stream.

        Parameters
        ----------
        hint: Optional[:class:`int`]
            Hint to the number of lines to read.
        timeout: Optional[:class:`float`]
            Timeout to wait for the read to complete.
        wait: :class:`bool`
            Whether to wait for data to be available.

        Raises
        ------
        asyncio.TimeoutError: If the timeout expires.
        """
        lines = []

        while True:
            try:
                line = await self.readline(timeout=timeout, wait=wait)
            except asyncio.TimeoutError:
                break
            
            if (hint is not None and len(lines) >= hint) or not line:
                break

            lines.append(line)

        return lines


class StreamProtocol(asyncio.Protocol):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        connection_callback: Callable[[StreamReader, StreamWriter], Any],
    ) -> None:
        self.loop = loop
        self.connection_callback = connection_callback
        self.reader = StreamReader(loop)
        self.writer: Optional[StreamWriter] = None
        self.paused = False
        self.waiter = loop.create_future()

    def __call__(self) -> Any:
        return self.__class__(self.loop, self.connection_callback)

    def connection_made(self, transport: Any) -> None:
        self.writer = writer = StreamWriter(transport, self.waiter)

        if utils.iscoroutinefunction(self.connection_callback):
            self.loop.create_task(self.connection_callback(self.reader, writer))
        else:
            self.connection_callback(self.reader, writer)

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        if exc:
            self.waiter.set_exception(exc)
        else:
            self.waiter.set_result(None)

        self.writer = None
        self.reader.reset()

    def data_received(self, data: bytes) -> None:
        self.reader.feed_data(data)

    def eof_received(self) -> None:
        self.reader.feed_eof()

    def resume_writing(self) -> None:
        if not self.writer or not self.paused:
            return

        self.paused = False
        self.writer.resume_writing()

    def pause_writing(self) -> None:
        if not self.writer or self.paused:
            return

        self.paused = True
        self.writer.pause_writing()

async def open_connection(
    host: Optional[str] = None, port: Optional[int] = None, **kwargs: Any
) -> Tuple[StreamReader, StreamWriter]:
    """
    Opens a connection to a remote host.

    Parameters
    -----------
    host: Optional[:class:`str`]
        The host to connect to.
    port: Optional[:class:`int`]
        The port to connect to.
    **kwargs: Any
        Additional keyword arguments to pass to :meth:`asyncio.loop.create_connection`.
    """
    loop = kwargs.pop('loop', None) or compat.get_running_loop()
    protocol = StreamProtocol(loop, lambda w, r: None)

    _, proto = await loop.create_connection(protocol, host=host, port=port, **kwargs) # type: ignore
    return proto.reader, proto.writer


async def start_server(
    connection_callback: Callable[[StreamReader, StreamWriter], Any],
    host: Optional[str] = None,
    port: Optional[int] = None,
    **kwargs: Any
) -> asyncio.AbstractServer:
    """
    Starts a server.

    Parameters
    -----------
    connection_callback: Callable[[:class:`~StreamReader`, :class:`~StreamWriter`], Any]
        The callback to call when a connection is made.
    host: Optional[:class:`str`]
        The host to listen on.
    port: Optional[:class:`int`]
        The port to listen on.
    **kwargs: Any
        Additional keyword arguments to pass to :meth:`asyncio.loop.create_server`.
    """
    loop = kwargs.pop('loop', None) or compat.get_running_loop()
    protocol = StreamProtocol(loop, connection_callback)

    server = await loop.create_server(protocol, host=host, port=port, **kwargs)  # type: ignore
    return server


async def start_unix_server(
    connection_callback: Callable[[StreamReader, StreamWriter], Any],
    path: Optional[str] = None,
    **kwargs: Any
) -> asyncio.AbstractServer:
    """
    Starts a Unix server.

    Note
    ----
    This only works on unix based systems.

    Parameters
    -----------
    connection_callback: Callable[[:class:`~StreamReader`, :class:`~StreamWriter`], Any]
        The callback to call when a connection is made.
    path: Optional[:class:`str`]
        The path of the unix domain socket.
    **kwargs: Any
        Additional keyword arguments to pass to :meth:`asyncio.loop.create_unix_server`.

    """
    loop = kwargs.pop('loop', None) or compat.get_running_loop()
    protocol = StreamProtocol(loop, connection_callback)

    server = await loop.create_unix_server(protocol, path=path, **kwargs)  # type: ignore
    return server

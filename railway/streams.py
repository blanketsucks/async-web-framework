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
from typing import List, Optional, Union, Any
import asyncio

from . import compat, utils

__all__ = (
    'StreamWriter',
    'StreamReader',
    'StreamTransport',
    'StreamProtocol',
    'open_connection',
)

class StreamWriter:
    """
    Parameters
    -----------
    transport: :class:`asyncio.Transport`
        The transport to use.
    """
    def __init__(self, transport: asyncio.Transport) -> None:
        self._transport = transport
        self._waiter: 'Optional[asyncio.Future[None]]' = None

        self._loop = compat.get_running_loop()

    @property
    def transport(self) -> asyncio.Transport:
        """
        The transport used by this writer
        """
        return self._transport

    async def _wait_for_drain(self, timeout: float=None) -> None:
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

    async def write(self, data: Union[bytearray, bytes], *, timeout: float=None) -> None:
        """
        Writes data to the transport.

        Parameters
        ----------
        data: Union[:class:`bytearray`, :class:`bytes`]
            data to write.
        timeout: Optional[:class:`float`]
            timeout to wait for the write to complete.

        Raises
        ------
        asyncio.TimeoutError: if the timeout expires.
        """
        self._transport.write(data)
        await self._wait_for_drain(timeout)

    async def writelines(self, data: List[Union[bytearray, bytes]], *, timeout: float=None) -> None:
        """
        Writes a list of data to the transport.

        Parameters
        ----------
        data: List[Union[:class:`bytearray`, :class:`bytes`]]
            list of data to write.
        timeout: Optional[:class:`float`]
            timeout to wait for the write to complete.

        Raises
        ------
        asyncio.TimeoutError: if the timeout expires.
        """
        self._transport.writelines(data)
        await self._wait_for_drain(timeout)

    def get_extra_info(self, name: str, default: Any=None) -> Any:
        """
        Get optional transport information.

        Parameters
        ----------
        name: :class:`str`
            The name of the information.
        default: Any
            The default value to return if the information is not available.
        """
        return self._transport.get_extra_info(name, default)

    def close(self):
        """
        Closes the transport.
        """
        self._transport.close()

class StreamReader:
    """
    Attributes
    ----------
    buffer: :class:`bytearray`
        A bytearray containing the data.
    loop: :class:`asyncio.AbstractEventLoop`
        A reference to the event loop.

    Example
    -------
    .. code-block:: python3

        import asyncio
        import railway

        class Protocol(asyncio.Protocol):
            def __init__(self):
                self.reader = None
                self.writer = None

            def connection_made(self, transport: asyncio.Transport):
                self.reader = railway.StreamReader()
                self.writer = railway.StreamWriter(transport)

            def data_received(self, data: bytes):
                self.reader.feed_data(data)

            def eof_received(self):
                self.reader.feed_eof()

            def connection_lost(self, exc: Optional[Exception]):
                self.reader = None
                self.writer = None
        
        async def main():
            loop = asyncio.get_running_loop()
            _, protocol = await loop.create_connection(lambda: Protocol(), 'somewhere', 12345)

            reader = protocol.reader
            writer = protocol.writer

            await writer.write(b'stuff')
            data = await reader.read()

            print(data)

            writer.close()
        
        asyncio.run(main())
        
        # The above example might be bad but it's just a showcase of how to use the class.
    """
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        self.buffer: bytearray = bytearray()
        self.loop: asyncio.AbstractEventLoop = loop or compat.get_running_loop()

        self._waiter: Optional[asyncio.Future[None]] = None

    async def _wait_for_data(self, timeout: Optional[float]=None):
        self._waiter = self.loop.create_future()

        try:
            await asyncio.wait_for(self._waiter, timeout)
        finally:
            self._waiter = None

    def feed_data(self, data: Union[bytearray, bytes]) -> None:
        """
        Feeds the data to the reader.

        Parameters
        ----------
        data: Union[:class:`bytearray`, :class:`bytes`]
            data to be fed.
        """
        self.buffer.extend(data)

        if self._waiter:
            try:
                self._waiter.set_result(None)
            except asyncio.InvalidStateError:
                pass

    def feed_eof(self):
        return

    async def read(self, nbytes: Optional[int]=None, *, timeout: Optional[float]=None) -> bytes:
        """
        Reads ``nbytes`` off the stream. If ``nbytes`` is not provided, reads the whole stream.

        Parameters
        ----------
        nbytes: :class:`int`
            Number of bytes to read.
        timeout: Optional[:class:`float`]
            Timeout to wait for the read to complete.

        Raises
        ------
        asyncio.TimeoutError: If the timeout expires.
        """
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

    async def readline(self, *, timeout: Optional[float]=None, wait: bool=True) -> Optional[bytes]:
        """
        Reads a line off the stream.

        Parameters
        ----------
        timeout: Optional[:class:`float`]
            Timeout to wait for the read to complete.

        Raises
        ------
        asyncio.TimeoutError: If the timeout expires.
        """
        if not self.buffer:
            await self._wait_for_data(timeout=timeout)

        index = self.buffer.find(b'\n')

        if not wait and index == -1:
            return None
        
        while index == -1:
            await self._wait_for_data(timeout=timeout)
            index = self.buffer.find(b'\n')

        data = self.buffer[:index]
        self.buffer = self.buffer[index + 1:]

        return bytes(data)

    async def readlines(self, size: int=None, *, timeout: float=None):
        """
        Reads a list of lines off the stream.

        Parameters
        ----------
        size: :class:`int`
            The maximum number of bytes to read.
        timeout: Optional[:class:`float`]
            Timeout to wait for the read to complete.

        Raises
        ------
        asyncio.TimeoutError: If the timeout expires.
        """
        data = await self.readline(timeout=timeout, wait=False)

        while data is not None:
            yield data
            data = await self.readline(timeout=timeout, wait=False)

class StreamTransport:
    """
    A wrapper around a :class:`asyncio.Transport` that provides
    :class:`~railway.streams.StreamWriter` and :class:`~railway.streams.StreamReader` functionality
    """
    def __init__(self, transport: asyncio.Transport, waiter: asyncio.Future[None]) -> None:
        self._transport = transport
        self._waiter = waiter
        self._writer = StreamWriter(transport)
        self._reader = StreamReader()

        self.loop = self._reader.loop


    @utils.copy_docstring(StreamWriter.get_extra_info)
    def get_extra_info(self, name: str, default: Any=None) -> Any:
        return self._writer.get_extra_info(name, default)

    @utils.copy_docstring(asyncio.Transport.get_protocol)
    def get_protocol(self) -> asyncio.BaseProtocol:
        return self._transport.get_protocol()

    def close(self):
        """
        Closes the transport.
        """
        self._writer.close()

    async def wait_closed(self) -> None:
        await self._waiter

    def abort(self):
        """
        Closes the transport immediately.
        """
        return self._transport.abort()

    def is_closing(self):
        """
        True if the transport is closing.
        """
        return self._transport.is_closing()

    def is_reading(self):
        """
        True if the transport is reading.
        """
        return self._transport.is_reading()

    @utils.copy_docstring(StreamReader.feed_data)
    def feed_data(self, data: Union[bytes, bytearray]):
        self._reader.feed_data(data)

    def feed_eof(self):
        self._reader.feed_eof()

    @utils.copy_docstring(StreamReader.read)
    async def receive(self, nbytes: Optional[int]=None, *, timeout: Optional[float]=None) -> bytes:
        return await self._reader.read(nbytes, timeout=timeout)

    @utils.copy_docstring(StreamWriter.write)
    async def write(self, data: Union[bytearray, bytes], *, timeout: Optional[float]=None):
        await self._writer.write(data, timeout=timeout)

    @utils.copy_docstring(StreamWriter.writelines)
    async def writelines(self, data: List[Union[bytearray, bytes]], *, timeout: Optional[float]=None):
        await self._writer.writelines(data, timeout=timeout)

    def pause_writing(self) -> None:
        """
        Creates a future that is resolved when :meth:~`.StreamTransport.resume_writing` is called.
        This is supposed to be called when :meth:`asyncio.Protocol.pause_writing` is called.
        """
        self._writer.pause_writing()
    
    def resume_writing(self) -> None:
        """
        Sets the future that was created by :meth:~`.StreamTransport.pause_writing` to be resolved.
        This is supposed to be called when :meth:`asyncio.Protocol.resume_writing` is called.
        """
        self._writer.resume_writing()

class StreamProtocol(asyncio.Protocol):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

        self.transport: Optional[StreamTransport] = None
        self.waiter: Optional[asyncio.Future] = None

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self

    def connection_made(self, transport: Any) -> None:
        self.waiter = waiter = self.loop.create_future()
        self.transport = StreamTransport(transport, waiter)
    
    def connection_lost(self, exc: Optional[BaseException]) -> None:
        if self.waiter:
            if not self.waiter.done():
                self.waiter.set_result(None)
    
    def data_received(self, data: bytes) -> None:
        if not self.transport:
            return

        self.transport.feed_data(data)

    def eof_received(self) -> None:
        if not self.transport:
            return

        self.transport.feed_eof()

    def resume_writing(self) -> None:
        if not self.transport:
            return

        self.transport.resume_writing()

    def pause_writing(self) -> None:
        if not self.transport:
            return

        self.transport.pause_writing()

async def open_connection(host: str, port: int, **kwargs: Any):
    loop = compat.get_running_loop()
    protocol = StreamProtocol(loop)

    await loop.create_connection(
        protocol,
        host=host,
        port=port,
        **kwargs
    )

    if not protocol.transport:
        raise RuntimeError('Connection failed')

    return protocol.transport

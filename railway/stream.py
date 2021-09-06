from typing import List, Optional, Union, Any
import asyncio

from . import compat

__all__ = (
    'StreamWriter',
    'StreamReader'
)

class StreamWriter:
    def __init__(self, transport: asyncio.Transport) -> None:
        """
        StreamWriter constructor.

        Args:
            transport: an `asyncio.Transport`
        """
        self._transport = transport
        self._waiter: 'Optional[asyncio.Future[None]]' = None

    @property
    def transport(self) -> asyncio.Transport:
        """
        Returns:
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

    async def write(self, data: Union[bytearray, bytes], *, timeout: float=None) -> None:
        """
        Writes data to the transport.

        Args:
            data: data to write.
            timeout: timeout to wait for the write to complete.

        Raises:
            asyncio.TimeoutError: if the timeout expires.
        """
        self._transport.write(data)
        await self._wait_for_drain(timeout)

    async def writelines(self, data: List[Union[bytearray, bytes]], *, timeout: float=None) -> None:
        """
        Writes a list of data to the transport.

        Args:
            data: list of data to write.
            timeout: timeout to wait for the write to complete.

        Raises:
            asyncio.TimeoutError: if the timeout expires.
        """
        self._transport.writelines(data)
        await self._wait_for_drain(timeout)

    def get_extra_info(self, name: str, default: Any=None) -> Any:
        """
        Get optional transport information.

        Args:
            name: the name of the information.
            default: the default value to return if the information is not available.
        
        Returns:
            The requested information.
        """
        return self._transport.get_extra_info(name, default)

    def close(self):
        """
        Closes the transport.
        """
        self._transport.close()

class StreamReader:
    """
    Attributes:
        buffer: A bytearray containing the data.
        loop: A reference to the event loop.

    Example:
        ```py
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
        ```
        The above example might be bad but it's just a showcase of how to use the class.
        
    
    """
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        """
        StreamReader constructor.

        Args:
            loop: an `asyncio.AbstractEventLoop`
        """
        self.buffer: bytearray = bytearray()
        self.loop: asyncio.AbstractEventLoop = loop or compat.get_running_loop()

        self._waiter = None

    async def _wait_for_data(self, timeout: Optional[float]=None):
        self._waiter = self.loop.create_future()

        try:
            await asyncio.wait_for(self._waiter, timeout)
        finally:
            self._waiter = None

    def feed_data(self, data: Union[bytearray, bytes]) -> None:
        """
        Feeds the data to the reader.

        Args:
            data: data to be fed.
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
        Reads `nbytes` from the stream. If `nbytes` is not provided, reads the whole stream.

        Args:
            nbytes: Number of bytes to read.
            timeout: Timeout to wait for the read to complete.

        Returns:
            The read data.

        Raises:
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
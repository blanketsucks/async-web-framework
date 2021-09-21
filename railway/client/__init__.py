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
import os
import ssl
from typing import Any, Union, List, Optional
import socket

from railway.streams import StreamTransport
from railway import compat

__all__ = (
    'ClientProtocol', 
    'Client', 
    'create_connection'
)

class ClientProtocol(asyncio.Protocol):
    """
    A subclass of `asyncio.Protocol` that implements the client side of a connection.

    Attributes:
        loop: The event loop to use.
        reader: The [StreamReader](./streams.md) object.
        writer: The [StreamWriter](./streams.md) object.
        waiter: a close waiter, in other words, an `asyncio.Future` that is set when the connection gets closed.
    """ 
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

        self.transport = None

        self.waiter = None

    def __call__(self):
        return self

    def connection_made(self, transport: asyncio.Transport) -> None: # type: ignore
        self.transport = StreamTransport(transport)
        self.waiter = self.loop.create_future()

    def data_received(self, data: bytes) -> None:
        if not self.transport:
            return

        self.transport.feed_data(data)

    def pause_writing(self) -> None:
        if not self.transport:
            return

        writer = self.transport._writer
        if not writer._waiter:
            writer._waiter = self.loop.create_future() # type: ignore
    
    def resume_writing(self) -> None:
        if not self.transport:
            return

        self.transport._wakeup_writer()

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            raise exc

        if not self.waiter:
            return

        self.waiter.set_result(None)
        self.waiter = None

    async def wait_for_close(self):
        """
        Waits for the connection to close.
        """
        if self.waiter:
            await self.waiter

class Client:
    """
    A class representing a client.

    Attributes:
        host: The host to connect to.
        port: The port to connect to.
        ssl_context: The SSL context to use.
        loop: The event loop to use.
        sock: The `socket.socket` to use.
    """
    def __init__(self, 
                host: Optional[str]=None, 
                port: Optional[int]=None, 
                *,
                sock: Optional[socket.socket]=None, 
                ssl_context: Optional[Union[ssl.SSLContext, Any]]=None,
                loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        self.host: str = host
        self.port: int = port

        if sock:
            if host or port:
                raise ValueError('Both host and port must be None if sock is specified')

        self.sock: socket.socket = sock

        self.ssl_context: ssl.SSLContext = ssl_context
        self.loop: asyncio.AbstractEventLoop = loop or compat.get_running_loop()

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

    def is_connected(self) -> bool:
        """
        Returns:
            True if the client is connected.
        """
        return self._connected and self._protocol is not None

    def is_closed(self) -> bool:
        """
        Returns:
            True if the client is closed.
        """
        return self._closed

    def is_ssl(self) -> bool:
        """
        Returns:
            True if the client is using SSL.
        """
        return self.ssl_context is not None and isinstance(self.ssl_context, ssl.SSLContext)

    async def connect(self) -> 'Client':
        """
        Connects to the host and port previously set by the constructor.

        Returns:
            The client itself.
        """
        self._protocol = protocol = ClientProtocol(self.loop)
        await self.loop.create_connection(
            protocol, self.host, self.port, sock=self.sock, ssl=self.ssl_context
        )

        self._connected = True
        return self

    async def write(self, data: Union[bytearray, bytes], *, timeout: Optional[float]=None) -> None:
        """
        Writes data to the transport.

        Parameters:
            data: The data to write.
            timeout: The timeout to use.

        Raises:
            asyncio.TimeoutError: If the timeout is exceeded.
        """
        self._ensure_connection()
        await self._protocol.transport.write(data, timeout=timeout) # type: ignore
    
    async def writelines(self, data: List[Union[bytearray, bytes]], *, timeout: Optional[float]=None):
        """
        Writes a list of data to the transport.

        Parameters:
            data: The data to write.
            timeout: The timeout to use.

        Raises:
            asyncio.TimeoutError: If the timeout is exceeded.
        """
        self._ensure_connection()
        await self._protocol.transport.writelines(data, timeout=timeout) # type: ignore

    async def receive(self, nbytes: Optional[int]=None, *, timeout: Optional[float]=None) -> bytes:
        """
        Reads data from the transport.

        Parameters:
            nbytes: The number of bytes to read.
            timeout: The timeout to use.

        Returns:
            The data read.

        Raises:
            asyncio.TimeoutError: If the timeout is exceeded.
        """
        self._ensure_connection()
        return await self._protocol.transport.read(nbytes, timeout=timeout) # type: ignore

    async def close(self) -> None:
        """
        Closes the connection.
        """
        self._ensure_connection()

        self._protocol.transport.close() # type: ignore
        await self._protocol.wait_for_close() # type: ignore

        self._closed = True

def create_connection(
    host: str, 
    port: int, 
    *, 
    ssl_context: Optional[Union[ssl.SSLContext, Any]]=None, 
    loop: Optional[asyncio.AbstractEventLoop]=None
):
    """
    A helper function to create a client.

    Parameters:
        host: The host to connect to.
        port: The port to connect to.
        ssl_context: The SSL context to use.
        loop: The event loop to use.
    """
    client = Client(host, port, ssl_context=ssl_context, loop=loop)
    return client

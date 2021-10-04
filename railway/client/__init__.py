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
import ssl
from typing import Any, Union, List, Optional, cast
import socket

from railway.streams import open_connection
from railway import compat

__all__ = (
    'Client', 
    'create_connection'
)

class Client:
    """
    A class representing a client.

    Parameters
    ----------
    host: :class:`str`
        The host to connect to.
    port: :class:`int`
        The port to connect to.
    ssl_context: :class:`ssl.SSLContext`
        The SSL context to use.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop to use.
    sock: :class:`socket.socket`
        The socket to use.
    """
    def __init__(self, 
                host: Optional[str]=None, 
                port: Optional[int]=None, 
                *,
                sock: Optional[socket.socket]=None, 
                ssl_context: Optional[Union[ssl.SSLContext, Any]]=None,
                loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        self.host = host or 'localhost'
        self.port = port or 5000

        if sock:
            if host or port:
                raise ValueError('Both host and port must be None if sock is specified')

        self.sock = sock

        self.ssl_context = ssl_context
        self.loop = loop or compat.get_running_loop()

        self._stream = None

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
        True if the client is connected.
        """
        return self._connected and self._stream is not None

    def is_closed(self) -> bool:
        """
        True if the client is closed.
        """
        return self._closed

    def is_ssl(self) -> bool:
        """
        True if the client is using SSL.
        """
        return self.ssl_context is not None and isinstance(self.ssl_context, ssl.SSLContext)

    async def connect(self) -> 'Client':
        """
        Connects to the host and port previously set by the constructor.
        """
        self._stream = await open_connection(
            self.host, 
            self.port, 
            ssl_context=self.ssl_context, 
            loop=self.loop,
            sock=self.sock
        )

        self._connected = True
        return self

    async def write(self, data: Union[bytearray, bytes], *, timeout: Optional[float]=None) -> None:
        """
        Writes data to the transport.

        Parameters
        ----------
        data: Union[:class:`bytes`, :class:`bytearray`]
            The data to write.
        timeout: :class:`float`
            The timeout to use.

        Raises
        ------
        asyncio.TimeoutError: 
            If the timeout is exceeded.
        """
        self._ensure_connection()
        await self._protocol.transport.write(data, timeout=timeout) # type: ignore
    
    async def writelines(self, data: List[Union[bytearray, bytes]], *, timeout: Optional[float]=None):
        """
        Writes a list of data to the transport.

        Parameters
        ----------
        data: Union[:class:`bytes`, :class:`bytearray`]
            The data to write.
        timeout: :class:`float`
            The timeout to use.

        Raises
        ------
        asyncio.TimeoutError: 
            If the timeout is exceeded.
        """
        self._ensure_connection()
        await self._protocol.transport.writelines(data, timeout=timeout) # type: ignore

    async def receive(self, nbytes: Optional[int]=None, *, timeout: Optional[float]=None) -> bytes:
        """
        Reads data from the transport.

        Parameters
        ----------
        nbytes: :class:`int`
            The number of bytes to read.
        timeout: :class:`float`
            The timeout to use.

        Raises
        ------
        asyncio.TimeoutError: 
            If the timeout is exceeded.
        """
        self._ensure_connection()
        return await self._protocol.transport.receive(nbytes, timeout=timeout) # type: ignore

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

    Parameters
    ----------
    host: :class:`str`
        The host to connect to.
    port: :class:`int`
        The port to connect to.
    ssl_context: :class:`ssl.SSLContext`
        The SSL context to use.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop to use.
    """
    client = Client(host, port, ssl_context=ssl_context, loop=loop)
    return client

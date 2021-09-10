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
import socket
from typing import Dict, List, Optional, Tuple, Union
import asyncio

__all__ = (
    'ConnectionTimeout',
    'Address',
    'HappyEyeballs',
    'AsyncHappyEyeballs'
)

class ConnectionTimeout(TimeoutError):
    pass

class Address:
    def __init__(self, 
                addr: Tuple[socket.AddressFamily, int, int, str, Union[Tuple[str, int], Tuple[str, int, int, int]]]
                ) -> None:
        self._addr = addr

        self.family = addr[0]
        self.type = addr[1]
        self.protocol = addr[2]
        self.canonname = addr[3]

    def __repr__(self) -> str:
        return f'<Address family={self.family!r} type={self.type!r} protocol={self.protocol!r} address={self.address()!r}>'

    def address(self) -> Union[Tuple[str, int], Tuple[str, int, int, int]]:
        return self._addr[4]

class HappyEyeballs:
    """
    An implementation of the RFC 6555 protocol.\n
    Reference: [https://tools.ietf.org/html/rfc6555](https://tools.ietf.org/html/rfc6555)\n
    Wikipedia: [https://en.wikipedia.org/wiki/Happy_eyeballs](https://en.wikipedia.org/wiki/Happy_eyeballs)
    
    """
    def __init__(self) -> None:
        self._connected_sock: Optional[socket.socket] = None
        self._cache: Dict[Tuple[str, int], Address] = {}

    def _ensure_connection(self):
        if not self._connected_sock:
            raise ConnectionError('Not connected')

    def _getaddrinfo(self, host: str, port: int, type: socket.SocketKind) -> List[Address]:
        addrs = socket.getaddrinfo(host, port, type=type)
        return [Address(addr) for addr in addrs]

    def _filter_addresses(self, addrs: List[Address]) -> List[Address]:
        filtered = []

        found_ipv4 = False
        found_ipv6 = not socket.has_ipv6

        for addr in addrs:
            if addr.family == socket.AF_INET6 and not found_ipv6:
                filtered.append(addr)
                found_ipv6 = True

            if addr.family == socket.AF_INET and not found_ipv4:
                filtered.append(addr)
                found_ipv4 = True

        return filtered

    def _wait_for_connection(self, 
                            sock: socket.socket, 
                            address: Union[Tuple[str, int], Tuple[str, int, int, int]], 
                            timeout: int) -> bool:
        sock.settimeout(timeout)

        try:
            sock.connect(address)
            return True
        except socket.timeout:
            sock.close()
            return False

    def _create_socket(self, family: socket.AddressFamily, type: socket.SocketKind) -> socket.socket:
        return socket.socket(family, type)

    def _connect_from_cache(self, host: str, port: int):
        addr = self._cache.get((host, port))
        if addr:
            sock = self._create_socket(addr.family, addr.type)
            sock.connect(addr.address())

            self._connected_sock = sock
            return sock

        return None

    def _connect(self, host: str, port: int, addrs: List[Address]) -> socket.socket:
        filtered = self._filter_addresses(addrs)

        for addr in filtered:
            sock = self._create_socket(addr.family, addr.type)

            address = addr.address()
            if self._wait_for_connection(sock, address, 0.3):
                self._connected_sock = sock
                self._cache[(host, port)] = addr

                return sock

        sock = self._create_socket(socket.AF_INET, socket.SOCK_STREAM)
        if self._wait_for_connection(sock, (host, port), 0.3):
            self._connected_sock = sock
            self._cache[(host, port)] = Address((socket.AF_INET, socket.SOCK_STREAM, 0, '', (host, port)))

            return sock

        raise ConnectionTimeout(f'Could not connect to {host}:{port}')

    def connect(self, host: str, port: int, *, socket_type: Optional[socket.SocketKind]=None) -> socket.socket:
        """
        Connects to the given host and port.
        
        It tries to priotize IPv6 over IPv4, and will try to connect to the first of both protocols.
        The way those addresses are filtered is by using [socket.getaddrinfo](https://docs.python.org/3/library/socket.html#socket.getaddrinfo).

        If both connections fail, it will try to connect to the originally given host and port from this method,
        if the connections to the original host and port fail too, it will raise a `ConnectionTimeout` exception. 
        Otherwise it returns a socket.

        Parameters:
            host: The host to connect to.
            port: The port to connect to.
            socket_type: The socket type to use.

        Returns:
            A `socket.socket`.
        """
        if not socket_type:
            socket_type = socket.SOCK_STREAM
    
        sock = self._connect_from_cache(host, port)
        if sock:
            return sock

        addrs = self._getaddrinfo(host, port, socket_type)
        return self._connect(host, port, addrs)

    def send(self, data: bytes) -> None:
        """
        Sends data to the connected socket.

        Parameters:
            data: The data to send.

        Raises:
            ConnectionError: If the socket is not connected.
        """
        self._ensure_connection()
        self._connected_sock.send(data)

    def recv(self, size: int) -> bytes:
        """
        Recieves data from the connected socket.

        Parameters:
            size: The number of bytes to receive.
        
        Returns:
            The read data.

        Raises:
            ConnectionError: If the socket is not connected.
        """
        self._ensure_connection()
        return self._connected_sock.recv(size)

    def close(self) -> None:
        """
        Closes the connection.

        Raises:
            ConnectionError: If the socket is not connected.
        """
        self._ensure_connection()
        self._connected_sock.close()

        self._connected_sock = None

class AsyncHappyEyeballs(HappyEyeballs):
    def __init__(self) -> None:
        self._loop = asyncio.get_event_loop()
        super().__init__()

    async def _getaddrinfo(self, host: str, port: int, type: socket.SocketKind) -> List[Address]:
        addrs = await self._loop.getaddrinfo(host, port, type=type)
        return [Address(addr) for addr in addrs]

    async def _wait_for_connection(self, 
                            sock: socket.socket, 
                            address: Union[Tuple[str, int], Tuple[str, int, int, int]], 
                            timeout: int) -> bool:
        sock.settimeout(timeout)

        try:
            await self._loop.sock_connect(sock, address)
            return True
        except socket.timeout:
            sock.close()
            return False

    async def _connect_from_cache(self, host: str, port: int) -> Optional[socket.socket]:
        addr = self._cache.get((host, port))
        if addr:
            sock = self._create_socket(addr.family, addr.type)
            await self._loop.sock_connect(sock, addr.address())

            self._connected_sock = sock
            return sock

        return None

    async def _connect(self, host: str, port: int, addrs: List[Address]) -> socket.socket:
        filtered = self._filter_addresses(addrs)

        for addr in filtered:
            sock = self._create_socket(addr.family, addr.type)

            address = addr.address()
            if await self._wait_for_connection(sock, address, 0.3):
                self._connected_sock = sock
                self._cache[(host, port)] = addr

                return sock

        raise Exception('No connection available')

    async def connect(self, host: str, port: int, *, socket_type: Optional[socket.SocketKind]=None) -> socket.socket:
        if not socket_type:
            socket_type = socket.SOCK_STREAM

        sock = await self._connect_from_cache(host, port)
        if sock:
            return sock

        addrs = await self._getaddrinfo(host, port, socket_type)
        return await self._connect(host, port, addrs)

    async def send(self, data: bytes) -> None:
        self._ensure_connection()
        await self._loop.sock_sendall(self._connected_sock, data)
        
    async def recv(self, size: int) -> bytes:
        self._ensure_connection()
        return await self._loop.sock_recv(self._connected_sock, size)

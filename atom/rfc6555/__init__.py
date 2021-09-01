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

    def _create_socket(self, family: socket.AddressFamily) -> socket.socket:
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

        raise ConnectionTimeout(f'Could not connect to {host}:{port}')

    def connect(self, host: str, port: int, *, socket_type: Optional[socket.SocketKind]=None):
        if not socket_type:
            socket_type = socket.SOCK_STREAM
    
        sock = self._connect_from_cache(host, port)
        if sock:
            return sock

        addrs = self._getaddrinfo(host, port, socket_type)
        return self._connect(host, port, addrs)

    def send(self, data: bytes) -> None:
        self._ensure_connection()
        self._connected_sock.send(data)

    def recv(self, size: int) -> bytes:
        self._ensure_connection()
        return self._connected_sock.recv(size)

    def close(self) -> None:
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

    async def connect(self, host: str, port: int, *, socket_type: Optional[socket.SocketKind]=None):
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
import socket as _socket
import ssl as _ssl
import asyncio
import concurrent.futures
import functools
import typing
import sys
import ipaddress

from .utils import (
    ConnectionContextManager,
    ServerContextManager,
)
from .protocols import Protocol
from . import transports

if typing.TYPE_CHECKING:
    from .websockets import Websocket


class InvalidAddress(Exception):
    ...

class SSLSocketRequired(Exception):
    ...

__all__ = (
    'socket',
    'Address',
    'HostAddress',
    'Family',
    'Type',
)

Family = _socket.AddressFamily
Type = _socket.SocketKind

class HostAddress:
    def __init__(self, host: typing.Tuple[str, typing.List[str], typing.List[str]]) -> None:
        self.host = host

    def __repr__(self) -> str:
        return '<RetAddress hostname={0.hostname!r}>'.format(self)

    @property
    def hostname(self):
        return self.host[0]

    @property
    def aliases(self):
        return self.host[1]

    @property
    def ipaddrlist(self):
        return self.host[2]

class Address:
    def __init__(self, 
                __addr: typing.Tuple[str, int], 
                __socket: typing.Union['socket', 'Websocket']):

        self.__addr = __addr
        self._socket = __socket

    def __repr__(self) -> str:
        return '<Address host={0.host!r} port={0.port}>'.format(self)

    @property
    def host(self) -> str:
        return self.__addr[0]

    @host.setter
    def host(self, value):
        if not isinstance(value, str):
            raise ValueError('Hosts must be a string')

        self.__addr = (value, self.port)

    @property
    def port(self) -> int:
        return self.__addr[1]

    @port.setter
    def port(self, value):
        if not isinstance(value, int):
            raise ValueError('Ports must be an integer')

        self.__addr = (self.host, value)

    @classmethod
    def from_host_and_port(cls, 
                        host: str, 
                        port: int, 
                        *, 
                        socket: typing.Union['socket', 'Websocket']):

        addr = (host, port)
        return cls(addr, socket)

    async def getinfo(self):
        addrinfo = await self._socket.getaddrinfo(self.host, self.port)
        return addrinfo
    
    async def gethost(self) -> typing.Union[str, HostAddress]:
        if not self._socket._is_ip(self.host):
            host = await self._socket.gethostbyname(self.host)
            return host

        host = await self._socket.gethostbyaddr(self.host)
        return host

    def as_tuple(self):
        return (self.host, self.port)

class socket:
    def __init__(self,
                family: int = Family.AF_INET,
                type: int = Type.SOCK_STREAM,
                proto: int = 0, 
                fileno: int = ...,
                *,
                socket: _socket.socket = ..., 
                ssl: _ssl.SSLContext = ..., 
                loop: asyncio.AbstractEventLoop = ...,
                executor: concurrent.futures.Executor = ...):

        fileno = None if fileno is ... else fileno
        
        if socket is ...:
            self._socket = _socket.socket(family, type, proto, fileno)
        else:
            self._socket = socket

        if ssl is ...:
            self.__ssl = _ssl.create_default_context()
        else:
            self.__ssl = ssl

        if loop is ...:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

        if executor is ...:
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)
        else:
            self._executor = executor
        
        self._closed = False
        self._connected = False
        self._bound = False

        self.settimeout(1)

    def __repr__(self) -> str:
        name = self.__class__.__name__
        s = f'<{name} '

        if self._closed:
            s += '[closed] '

        attrs = {
            'fd': self.fileno,
            'family': self.family,
            'type': self.type,
            'proto': self.proto,
        }

        if self._connected:
            attrs['laddr'] = self._laddr
            attrs['raddr'] = self._raddr

        s += ' '.join([f'{k}={v!r}' for k, v in attrs.items()])
        s += '>'

        return s

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.close()
        return self

    @staticmethod
    def __platform_check(name: str):
        return sys.platform.startswith(name)

    async def _run_in_executor(self, name: str, *args, **kwargs):
        method = getattr(self._socket, name, None)
        if not method:
            method = getattr(_socket, name)

        executor = self._executor
        partial = functools.partial(method, *args, **kwargs)

        result = await self.loop.run_in_executor(
            executor, partial
        )
        return result

    async def _run_socket_operation(self, name: str, *args):
        if self.is_ssl:
            return await self._run_in_executor(name, *args)

        method = getattr(self.loop, 'sock_' + name)
        return await method(self._socket, *args)

    def _check_closed(self):
        if self._closed:
            raise RuntimeError('Cannot operate on a closed socket')

        return True

    def _check_connected(self):
        exc = RuntimeError

        if not self._connected:
            if not self._bound:
                raise exc('socket must be connected or bound to execute this operation')        

        return True

    async def _connect_with_ssl(self, address: Address, connect_ex: bool):
        self._check_closed()

        if self._connected:
            raise RuntimeError('socket already connected')

        if self._bound:
            raise RuntimeError('Can not connect a bound socket')

        host, port = address.as_tuple()

        hostname = await self._fetch_hostname(host)
        self._socket = self.__ssl.wrap_socket(self._socket, server_hostname=hostname)

        if not self._is_ip(host):
            host = await self.gethostbyname(host)

        addr = (host, port)

        try:
            if connect_ex:
                res = await self._run_in_executor('connect_ex', addr)
                return res

            self._connected = True
            await self._run_in_executor('connect', addr)
        except:
            raise ConnectionError('Could not connect to {0!r} on port {1!r}'.format(host, port))

        self._laddr = await self.getsockname()
        self._raddr = await self.getpeername()

        return self._raddr

    async def _connect_without_ssl(self, address: Address):
        self._check_closed()
        self.settimeout(0)

        if self._connected:
            raise RuntimeError('socket already connected')

        if self._bound:
            raise RuntimeError('Can not connect a bound socket')

        host, port = address.as_tuple()

        if not self._is_ip(host):
            host = await self.gethostbyname(host)

        addr = (host, port)

        await self._run_socket_operation('connect', addr)
        self._connected = True
        
        self._laddr = await self.getsockname()
        self._raddr = await self.getpeername()

        return self._raddr

    async def _connect(self, address: Address, connect_ex: bool, use_ssl: bool):
        host, port = address.as_tuple()

        if port == 443 or use_ssl:
            addr = await self._connect_with_ssl(address, connect_ex)
            return addr

        addr = await self._connect_without_ssl(address)
        return addr

    def _create_addr(self, host: str, port: int):
        return Address.from_host_and_port(host, port, socket=self)

    async def _fetch_hostname(self, ipaddress: str):   
        if self._is_ip(ipaddress):
            host = await self.gethostbyaddr(ipaddress)
            hostname = host.hostname
        else:
            hostname = ipaddress

        return hostname

    def _is_ip(self, string: str):
        try:
            ipaddress.ip_address(string)
        except ValueError:
            return False

        return True

    @property
    def ssl_context(self):
        return self.__ssl

    @property
    def family(self):
        return self._socket.family

    @property
    def type(self):
        return self._socket.type

    @property
    def proto(self):
        return self._socket.proto

    @property
    def fileno(self):
        return self._socket.fileno()

    @property
    def is_ssl(self):
        return isinstance(self._socket, _ssl.SSLSocket)

    @property
    def is_closed(self):
        return self._closed

    @property
    def is_connected(self):
        return self._connected

    @property
    def is_bound(self):
        return self._bound

    @property
    def laddr(self) -> typing.Optional[Address]:
        if not self._connected:
            return None

        return self._laddr

    @property
    def raddr(self) -> typing.Optional[Address]:
        if not self._connected:
            return None

        return self._raddr

    async def if_nameindex(self) -> typing.List[typing.Tuple[int, str]]:
        if self.__platform_check('darwin'):
            exc = 'the if_nameindex function is only available on windows and linux machines'
            raise OSError(exc)

        nameindex = await self._run_in_executor('if_nameindex')
        return nameindex

    async def if_nametoindex(self, name: str) -> int:
        if self.__platform_check('darwin'):
            exc = 'the if_nametoindex function is only available on windows and linux machines'
            raise OSError(exc)

        index = await self._run_in_executor('if_nametoindex', name)
        return index

    async def if_indextoname(self, index: int) -> str:
        if self.__platform_check('darwin'):
            exc = 'the if_indextoname function is only available on windows and linux machines'
            raise OSError(exc)

        name = await self._run_in_executor('if_indextoname', index)
        return name

    async def ioctl(self, control: int, option: typing.Union[int, typing.Tuple[int, int, int], bool]):
        if not self.__platform_check('win'):
            raise OSError('socket.ioctl() is only available on windows')

        await self._run_in_executor('ioctl', control, option)

    def share(self, process: int):
        if not self.__platform_check('win'):
            raise OSError('socket.share() is only available on windows')

        return self._socket.share(process)
        
    async def gethostbyaddr(self, address: str) -> HostAddress:
        if not self._is_ip(address):
            raise InvalidAddress(address)

        host = await self._run_in_executor('gethostbyaddr', address)
        return HostAddress(host)

    async def gethostbyname(self, name: str) -> str:
        host = await self._run_in_executor('gethostbyname', name)
        return host

    async def gethostbyname_ex(self, name: str) -> typing.Tuple[str, typing.List[str], typing.List[str]]:
        host = await self._run_in_executor('gethostbyname_ex', name)
        return host

    async def getaddrinfo(self, host: str, port: int, flags: int=...) -> typing.List[typing.Tuple[_socket.AddressFamily, _socket.SocketKind, int, str, typing.Union[typing.Tuple[str, int], typing.Tuple[str, int, int, int]]]]:
        if flags is ...:
            flags = 0

        addr = await self._run_in_executor('getaddrinfo', host, port, self.family, self.type, self.proto, flags)
        return addr

    async def getnameinfo(self,
                        sockaddr: typing.Union[typing.Tuple[str, int], typing.Tuple[str, int, int, int]], 
                        flags: int=...) -> typing.Tuple[str, str]:
        if flags is ...:
            flags = 0

        info = await self._run_in_executor('getnameinfo', sockaddr, flags)
        return info

    async def gethostname(self) -> str:
        host = await self._run_in_executor('gethostname')
        return host

    async def getprotobyname(self, name: str) -> int:
        proto = await self._run_in_executor('getprotobyname', name)
        return proto

    async def getservbyname(self, service: str, protocol: str) -> int:
        serv = await self._run_in_executor('getservbyname', service, protocol)
        return serv

    async def getservbyport(self, port: int, protocol: str) -> str:
        serv = await self._run_in_executor('getservbyport', port, protocol)
        return serv

    def inet_aton(self, ipaddress: str) -> bytes:
        return _socket.inet_aton(ipaddress)

    def inet_pton(self, family: int, ipaddress: str):
        return _socket.inet_pton(family, ipaddress)

    def inet_ntao(self, packed: bytes):
        return _socket.inet_ntoa(packed)

    def inet_ntop(self, family: int, packed: bytes):
        return _socket.inet_ntop(family, packed)

    def ntohl(self, x: int):
        return _socket.ntohl(x)

    def ntohs(self, x: int):
        return _socket.ntohs(x)

    def htonl(self, x: int):
        return _socket.htonl(x)

    def htons(self, x: int):
        return _socket.htons(x)

    def get_inheritable(self):
        return self._socket.get_inheritable()

    def set_inheritable(self, inheritable: bool):
        return self._socket.set_inheritable(inheritable)

    async def getpeername(self):
        self._check_closed()
        self._check_connected()

        peername = await self._run_in_executor('getpeername')
        return Address(peername, self)

    async def getsockname(self):
        self._check_closed()
        self._check_connected()

        sockname = await self._run_in_executor('getsockname')
        return Address(sockname, self)

    async def recv(self, nbytes: int=...) -> bytes:
        self._check_closed()
        self._check_connected()

        nbytes = 1024 if nbytes is ... else nbytes
        res = await self._run_socket_operation('recv', nbytes)

        return res

    async def recv_into(self, buffer: bytearray, nbytes: int=...) -> int:
        self._check_closed()
        self._check_connected()

        nbytes = 1024 if nbytes is ... else nbytes
        res = await self._run_socket_operation('recv_into', buffer, nbytes)

        return res

    async def recvfrom(self, bufsize: int=...) -> typing.Tuple[bytes, typing.Tuple[int, bytes]]:
        self._check_closed()
        self._check_connected()

        bufsize = 1024 if bufsize is ... else bufsize
        data, result = await self._run_in_executor('recvfrom', bufsize)

        return data, result

    async def recvfrom_into(self, buffer: bytearray, nbytes: int=...) -> typing.Tuple[int, typing.Tuple[int, bytes]]:
        self._check_closed()
        self._check_connected()

        nbytes = 1024 if nbytes is ... else nbytes
        res = await self._run_socket_operation('recvfrom_into', buffer, nbytes)

        return res

    async def recvall(self, nbytes: int=...) -> bytearray:
        self._check_closed()
        self._check_connected()

        frame = bytearray()
        last_chunk = False

        while True:
            if last_chunk:
                break

            try:
                data = await self.recv(nbytes)
            except:
                break

            if not data:
                break

            if data.endswith(b'\r\n\r\n'):
                last_chunk = True

            frame += data
        return frame

    async def send(self, data: bytes) -> int:
        self._check_closed()
        self._check_connected()

        res = await self._run_socket_operation('sendall', data)
        return res

    async def sendto(self, data: bytes, address: Address) -> int:
        self._check_closed()

        res = await self._run_in_executor('sendto', data, address.as_tuple())
        return res

    async def sendfile(self, file: typing.IO[bytes], *, offset: int=..., count: int=...):
        self._check_closed()
        self._check_connected()

        if offset is ...:
            offset = 0

        if count is ...:
            count = None

        return await self._run_socket_operation('sendfile', file, offset, count)

    async def connect(self, host: str, port: int, *, ssl: bool=...):
        ssl = False if ssl is ... else ssl

        addr = self._create_addr(host, port)
        await self._connect(addr, False, ssl)

        return addr

    async def connect_ex(self, host: str, port: int, *, ssl: bool=...):
        ssl = False if ssl is ... else ssl

        addr = self._create_addr(host, port)
        await self._connect(addr, True, ssl)
        
        return addr

    async def bind(self, host: str, port: int):
        self._check_closed()

        if self._bound:
            raise RuntimeError('socket is already bound')

        if self._connected:
            raise RuntimeError('Can not bind a connected socket')

        if not self._is_ip(host):
            host = await self.gethostbyname(host)

        try:
            await self._run_in_executor('bind', (host, port))
        except _socket.timeout:
            raise ConnectionError('Could not bind to {0!r} on port {1!r}'.format(host, port)) from None

        self._bound = True
        return self._create_addr(host, port)

    async def accept(self, timeout: int=...) -> typing.Tuple['socket', Address]:
        self._check_closed()

        timeout = 360 if timeout is ... else timeout
        self.settimeout(timeout)

        sock, addr = await self._run_in_executor('accept')
        client = self.__class__(
            socket=sock, 
            loop=self.loop, 
            executor=self._executor, 
            ssl=self.__ssl
        )

        client._bound = True

        client._laddr = await client.getsockname()
        client._raddr = await client.getpeername()

        return client, Address(addr, self)

    async def listen(self, backlog: int=...):
        self._check_closed()

        if backlog is ...:
            backlog = 5

        await self._run_in_executor('listen', backlog)
        return backlog
        
    def create_connection(self, host: str, port: int):
        return ConnectionContextManager(self, self._create_addr(host, port))

    def create_server(self, host: str, port: int, backlog: int=...):
        return ServerContextManager(self, self._create_addr(host, port), backlog)

    def duplicate(self):
        new = self.__class__(
            family=self.family,
            type=self.type,
            proto=self.proto,
            fileno=self.fileno,
            loop=self.loop,
            socket=self._socket,
            ssl=self.__ssl,
            executor=self._executor
        )

        return new

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            return self._socket.close()

        raise RuntimeError('Socket already closed')

    def shutdown(self, how: int):
        return self._socket.shutdown(how)

    def setsockopt(self, level: int, optname: int, value: typing.Union[int, bytes]):
        return self._socket.setsockopt(level, optname, value)
        
    def settimeout(self, timeout: int=...):
        if timeout is ...:
            timeout = 180.0

        self._socket.settimeout(timeout)
        return timeout

    def _create_transport(self, protocol, fut):
        transport = transports.Transport(
            socket=self,
            protocol=protocol,
            future=fut
        )
        return transport

    async def open_connection(self,
                            protocol: typing.Type[Protocol],
                            host: str,
                            port: int,
                            *,
                            ssl: bool=...):
        proto = protocol()

        await self.connect(
            host=host,
            port=port,
            ssl=ssl
        )

        await self._start_protocol(proto)

    async def _start_protocol(self, proto: Protocol):
        future = self.loop.create_future()

        transport = self._create_transport(
            protocol=proto,
            fut=future,
        )

        self.loop.create_task(
            coro=self._transport_read(transport)
        )

        await future

    async def _transport_read(self, transport: transports.Transport):
        while not transport.is_closed:

            await transport._wait()

            data = await self.recvall(32768)
            transport._data_received(bytes(data))

            transport._clear()
        
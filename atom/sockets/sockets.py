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
                        port, 
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
    def __init__(self, family=Family.AF_INET, type=Type.SOCK_STREAM, proto=0, 
                fileno=None, *, sock=None, ssl=None, loop=None, executor=None):

        if not sock:
            sock = _socket.socket(family, type, proto, fileno)

        if not ssl:
            ssl = _ssl.create_default_context()

        if not loop:
            loop = asyncio.get_event_loop()

        if not executor:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)
        
        self._ssl = ssl
        self._socket = sock
        self._executor = executor
        self.loop = loop
        self._closed = False
        self._connected = False
        self._bound = False

        self.settimeout(None)

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
        return None

    @staticmethod
    def __platform_check(name: str):
        return sys.platform.startswith(name)

    def _run_in_executor(self, func, *args, **kwargs):
        partial = functools.partial(func, *args, **kwargs)
        executor = self._executor

        future = self.loop.run_in_executor(
            executor, partial
        )
        return future

    def _run_socket_operation(self, func, *args, **kwargs):
        if self.is_ssl:
            return self._run_in_executor(func, *args, **kwargs)

        name = func.__name__

        method = getattr(self.loop, 'sock_' + name)
        return asyncio.ensure_future(method(self._socket, *args))

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

    async def _connect_with_ssl(self, address: Address):
        self._check_closed()

        if self._connected:
            raise RuntimeError('socket already connected')

        if self._bound:
            raise RuntimeError('Can not connect a bound socket')

        host, port = address.as_tuple()

        hostname = await self._fetch_hostname(host)
        self._socket = self._ssl.wrap_socket(self._socket, server_hostname=hostname)

        if not self._is_ip(host):
            host = await self.gethostbyname(host)

        addr = (host, port)

        try:
            self._connected = True
            await self._run_in_executor(self._socket.connect, addr)
        except:
            raise ConnectionError('Could not connect to {0!r} on port {1!r}'.format(host, port))

        self._laddr = await self.getsockname()
        self._raddr = await self.getpeername()

        return self._raddr

    async def _connect_without_ssl(self, address: Address):
        self._check_closed()

        if self._connected:
            raise RuntimeError('socket already connected')

        if self._bound:
            raise RuntimeError('Can not connect a bound socket')

        host, port = address.as_tuple()

        if not self._is_ip(host):
            host = await self.gethostbyname(host)

        addr = (host, port)

        await self._run_socket_operation(self._socket.connect, addr)
        self._connected = True
        
        self._laddr = await self.getsockname()
        self._raddr = await self.getpeername()

        return self._raddr

    async def _connect(self, address: Address, use_ssl: bool):
        host, port = address.as_tuple()

        if port == 443 or use_ssl:
            addr = await self._connect_with_ssl(address)
            return addr

        addr = await self._connect_without_ssl(address)
        return addr

    async def _connect_ex(self, address, ssl):
        self._check_closed()

        if self._connected:
            raise RuntimeError('socket already connected')

        if self._bound:
            raise RuntimeError('Can not connect a bound socket')

        host, port = address.as_tuple()

        hostname = await self._fetch_hostname(host)
        if port == 443 or ssl:
            self._socket = self._ssl.wrap_socket(self._socket, server_hostname=hostname)

        addr = (host, port)

        try:
            self._connected = True
            await self._run_in_executor(self._socket.connect_ex, addr)
        except:
            raise ConnectionError('Could not connect to {0!r} on port {1!r}'.format(host, port))

        self._laddr = await self.getsockname()
        self._raddr = await self.getpeername()

        return self._raddr

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
        return self._ssl

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

    async def if_nameindex(self):
        if self.__platform_check('win') or self.__platform_check('linux'):
            nameindex = await self._run_in_executor(_socket.if_nameindex)
            return nameindex

        exc = 'if_nameindex() is only available on windows and linux machines'
        raise OSError(exc)

    async def if_nametoindex(self, name):
        if self.__platform_check('win') or self.__platform_check('linux'):
            index = await self._run_in_executor(_socket.if_nametoindex, name)
            return index

        exc = 'if_nametoindex() is only available on windows and linux machines'
        raise OSError(exc)

    async def if_indextoname(self, index):
        if self.__platform_check('win') or self.__platform_check('linux'):
            name = await self._run_in_executor(_socket.if_indextoname, index)
            return name

        exc = 'if_indextoname() is only available on windows and linux machines'
        raise OSError(exc)

    async def ioctl(self, control, option):
        if not self.__platform_check('win'):
            raise OSError('ioctl() is only available on windows')

        await self._run_in_executor(self._socket.ioctl, control, option)

    def share(self, process):
        if not self.__platform_check('win'):
            raise OSError('share() is only available on windows')

        return self._socket.share(process)
        
    async def gethostbyaddr(self, address):
        if not self._is_ip(address):
            raise InvalidAddress(address)

        host = await self._run_in_executor(_socket.gethostbyaddr, address)
        return HostAddress(host)

    async def gethostbyname(self, name):
        host = await self._run_in_executor(_socket.gethostbyname, name)
        return host

    async def gethostbyname_ex(self, name):
        host = await self._run_in_executor(_socket.gethostbyname_ex, name)
        return host

    async def getaddrinfo(self, host, port, flags=0):
        addr = await self._run_in_executor(_socket.getaddrinfo, host, port, self.family, self.type, self.proto, flags)
        return addr

    async def getnameinfo(self, sockaddr, flags=0):
        info = await self._run_in_executor(_socket.getnameinfo, sockaddr, flags)
        return info

    async def gethostname(self):
        host = await self._run_in_executor(_socket.gethostname)
        return host

    async def getprotobyname(self, name):
        proto = await self._run_in_executor(_socket.getprotobyname, name)
        return proto

    async def getservbyname(self, service, protocol):
        serv = await self._run_in_executor(_socket.getservbyname, service, protocol)
        return serv

    async def getservbyport(self, port, protocol):
        serv = await self._run_in_executor(_socket.getservbyport, port, protocol)
        return serv

    def inet_aton(self, ipaddress):
        return _socket.inet_aton(ipaddress)

    def inet_pton(self, family, ipaddress):
        return _socket.inet_pton(family, ipaddress)

    def inet_ntao(self, packed):
        return _socket.inet_ntoa(packed)

    def inet_ntop(self, family, packed):
        return _socket.inet_ntop(family, packed)

    def ntohl(self, x):
        return _socket.ntohl(x)

    def ntohs(self, x):
        return _socket.ntohs(x)

    def htonl(self, x):
        return _socket.htonl(x)

    def htons(self, x):
        return _socket.htons(x)

    def get_inheritable(self):
        return self._socket.get_inheritable()

    def set_inheritable(self, inheritable: bool):
        return self._socket.set_inheritable(inheritable)

    async def getpeername(self):
        self._check_closed()
        self._check_connected()

        peername = await self._run_in_executor(self._socket.getpeername)
        return Address(peername, self)

    async def getsockname(self):
        self._check_closed()
        self._check_connected()

        sockname = await self._run_in_executor(self._socket.getsockname)
        return Address(sockname, self)

    async def recv(self, nbytes=None):
        self._check_closed()
        self._check_connected()

        nbytes = 1024 if not nbytes else nbytes

        res = await self._run_socket_operation(self._socket.recv, nbytes)
        return res

    async def recv_into(self, buffer, nbytes=None):
        self._check_closed()
        self._check_connected()

        nbytes = 1024 if not nbytes else nbytes

        res = await self._run_socket_operation(self._socket.recv_into, buffer, nbytes)
        return res

    async def recvfrom(self, bufsize=None):
        self._check_closed()
        self._check_connected()

        bufsize = 1024 if not bufsize else bufsize

        data, result = await self._run_in_executor(self._socket.recvfrom, bufsize)
        return data, result

    async def recvfrom_into(self, buffer, nbytes=None):
        self._check_closed()
        self._check_connected()

        nbytes = 1024 if not nbytes else nbytes

        res = await self._run_socket_operation(self._socket.recvfrom_into, buffer, nbytes)
        return res

    async def recvall(self, nbytes=None, buffer=None):
        self._check_closed()
        self._check_connected()

        if buffer:
            recv = functools.partial(self.recv_into, buffer)
        else:
            recv = self.recv

        frame = bytearray()
        while True:
            try:
                data = await recv(nbytes)
            except:
                break

            if not data:
                break

            frame += data

        if buffer:
            return None

        return frame


    async def recvmsg(self, bufsize, ancbufsize=0, flags=0):
        ...

    async def recvmsg_into(self, buffers, ancbufsize=0, flags=0): ...

    async def sendmsg(self):
        ...

    async def sendmsg_afalg(self):
        ...

    async def send(self, data):
        self._check_closed()
        self._check_connected()

        res = await self._run_socket_operation(self._socket.sendall, data)
        return res

    async def sendto(self, data, address):
        self._check_closed()

        res = await self._run_in_executor(self._socket.sendto, data, address.as_tuple())
        return res

    async def sendfile(self, file, *, offset=0, count=None):
        self._check_closed()
        self._check_connected()

        return await self._run_socket_operation(self._socket.sendfile, file, offset, count)

    async def connect(self, host, port, *, ssl=False):
        addr = self._create_addr(host, port)
        await self._connect(addr, ssl)

        return addr

    async def connect_ex(self, host, port, *, ssl=False):
        addr = self._create_addr(host, port)
        await self._connect_ex(addr, ssl)
        
        return addr

    async def bind(self, host, port):
        self._check_closed()

        if self._bound:
            raise RuntimeError('socket is already bound')

        if self._connected:
            raise RuntimeError('Can not bind a connected socket')

        if not self._is_ip(host):
            host = await self.gethostbyname(host)

        try:
            await self._run_in_executor(self._socket.bind, (host, port))
        except _socket.timeout:
            raise ConnectionError('Could not bind to {0!r} on port {1!r}'.format(host, port)) from None

        self._bound = True
        return self._create_addr(host, port)

    async def accept(self, timeout=None):
        self._check_closed()
        self.settimeout(timeout)

        sock, addr = await self._run_in_executor(self._socket.accept)
        client = self.__class__(
            sock=sock, 
            loop=self.loop, 
            executor=self._executor, 
            ssl=self._ssl
        )

        client._bound = True

        client._laddr = await client.getsockname()
        client._raddr = await client.getpeername()

        return client, Address(addr, self)

    async def listen(self, backlog=None):
        self._check_closed()

        await self._run_in_executor(self._socket.listen, backlog)
        return backlog
        
    def create_connection(self, host, port):
        return ConnectionContextManager(self, self._create_addr(host, port))

    def create_server(self, host, port, backlog=None):
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

    def shutdown(self, how):
        return self._socket.shutdown(how)

    def setsockopt(self, level, optname, value):
        return self._socket.setsockopt(level, optname, value)
        
    def settimeout(self, timeout=180.0):
        self._socket.settimeout(timeout)
        return timeout

    def _create_transport(self, protocol, fut):
        transport = transports.Transport(
            socket=self,
            protocol=protocol,
            future=fut,
            loop=self.loop
        )
        return transport

    async def open_connection(self, protocol, host, port, *, ssl=False):
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

        transport._loop_reading()
        await future

        
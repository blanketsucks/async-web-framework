import socket as _socket
import ssl as _ssl
import asyncio
import concurrent.futures
import functools
import typing
from http.server import BaseHTTPRequestHandler
import json
import sys
import ipaddress

from .utils import (
    HTTPConnectionContextManager,
    HTTPServerContextManager,
    ConnectionContextManager,
    ServerContextManager,
    check_ellipsis
)

class InvalidAddress(Exception):
    ...

class SSLSocketRequired(Exception):
    ...

__all__ = (
    'socket',
    'HTTPSocket',
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
                __socket: typing.Union['socket', 'HTTPSocket']):

        self.__addr = __addr
        self.__socket = __socket

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
                        socket: typing.Union['socket', 'HTTPSocket']):

        addr = (host, port)
        return cls(addr, socket)

    async def getinfo(self):
        addrinfo = await self.__socket.getaddrinfo(self.host, self.port)
        return addrinfo
    
    async def gethost(self) -> typing.Union[str, HostAddress]:
        if not self.__socket._is_ip(self.host):
            host = await self.__socket.gethostbyname(self.host)
            return host

        host = await self.__socket.gethostbyaddr(self.host)
        return host

    def as_tuple(self):
        return (self.host, self.port)

class socket:
    def __init__(self,
                family: int = Family.AF_INET,
                type: int = Type.SOCK_STREAM,
                proto: int = 0, 
                fileno: int = ...,
                timeout: int = ...,
                *,
                socket: _socket.socket = ..., 
                ssl: _ssl.SSLContext = ..., 
                loop: asyncio.AbstractEventLoop = ...,
                executor: concurrent.futures.Executor = ...) -> 'socket':

        fileno = None if fileno is ... else fileno
        
        if socket is ...:
            self.__socket = _socket.socket(family, type, proto, fileno)
        else:
            self.__socket = socket

        if ssl is ...:
            self.__ssl = _ssl.create_default_context()
        else:
            self.__ssl = ssl

        if loop is ...:
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop

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

    async def _run_in_executor(self, name: str, *args, **kwargs):
        method = getattr(self.__socket, name, None)
        if not method:
            method = getattr(_socket, name)

        executor = self._executor
        partial = functools.partial(method, *args, **kwargs)

        result = await self._loop.run_in_executor(
            executor, partial
        )
        return result

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

    def duplicate(self):
        new = self.__class__(
            family=self.family,
            type=self.type,
            proto=self.proto,
            fileno=self.fileno,
            loop=self._loop,
            socket=self.__socket,
            ssl=self.__ssl,
            executor=self._executor
        )

        return new

    @property
    def ssl_context(self):
        return self.__ssl

    @property
    def family(self):
        return self.__socket.family

    @property
    def type(self):
        return self.__socket.type

    @property
    def proto(self):
        return self.__socket.proto

    @property
    def fileno(self):
        return self.__socket.fileno()

    @property
    def is_ssl(self):
        return isinstance(self.__socket, _ssl.SSLSocket)

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

    @staticmethod
    def __platform_check(name: str):
        return sys.platform == name

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

    async def getaddrinfo(self, host: str, port: int) -> typing.List[typing.Tuple[_socket.AddressFamily, _socket.SocketKind, int, str, typing.Union[typing.Tuple[str, int], typing.Tuple[str, int, int, int]]]]:
        addr = await self._run_in_executor('getaddrinfo', host, port, self.family, self.type, self.proto)
        return addr

    async def getnameinfo(self,
                        sockaddr: typing.Union[typing.Tuple[str, int], typing.Tuple[str, int, int, int]], 
                        flags: int) -> typing.Tuple[str, str]:

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

    async def inet_aton(self, ipaddress: str) -> bytes:
        return await self._run_in_executor('inet_aton', ipaddress)

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

    def settimeout(self, timeout: int=...):
        if timeout is ...:
            timeout = 180.0

        self.__socket.settimeout(timeout)
        return timeout

    async def recv(self, nbytes: int=...) -> bytes:
        self._check_closed()
        self._check_connected()

        nbytes = 1024 if nbytes is ... else nbytes
        res = await self._run_in_executor('recv', nbytes)

        return res

    async def recvall(self, nbytes: int=...) -> bytes:
        self._check_closed()
        self._check_connected()

        frame = b''
        while True:
            try:
                data = await self.recv(nbytes)
            except _socket.timeout:
                break

            if not data:
                break

            frame += data
        
        return frame

    async def send(self, data: bytes) -> int:
        self._check_closed()
        self._check_connected()

        res = await self._run_in_executor('send', data)
        return res

    async def sendto(self, data: bytes, address: Address) -> int:
        self._check_closed()

        res = await self._run_in_executor('sendto', data, address.as_tuple())
        return res

    async def _connect(self, address: Address, connect_ex: bool, use_ssl: bool=False):
        self._check_closed()

        if self._connected:
            raise RuntimeError('socket already connected')

        if self._bound:
            raise RuntimeError('Can not connect a bound socket')

        host, port = address.as_tuple()

        if port == 443 or use_ssl:
            hostname = await self._fetch_hostname(host)
            self.__socket = self.__ssl.wrap_socket(self.__socket, server_hostname=hostname)

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

        return addr

    async def connect(self, host: str, port: int):
        addr = self._create_addr(host, port)
        await self._connect(addr, False)

        return addr

    async def connect_ex(self, host: str, port: int):
        addr = self._create_addr(host, port)
        await self._connect(addr, True)
        
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
            loop=self._loop, 
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

    async def makefile(self, mode: str=...):
        mode = 'r' if mode is ... else mode
        
    def create_connection(self, host: str, port: int):
        return ConnectionContextManager(self, self._create_addr(host, port))

    def create_server(self, host: str, port: int, backlog: int=...):
        return ServerContextManager(self, self._create_addr(host, port), backlog)

    def _create_addr(self, host: str, port: int):
        return Address.from_host_and_port(host, port, socket=self)

    async def _fetch_hostname(self, ipaddress: str):   
        if self._is_ip(ipaddress):
            host = await self.gethostbyaddr(ipaddress)
            print(host.aliases, host.hostname, host.host)
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

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            return self.__socket.close()

        raise RuntimeError('Socket already closed')

    def shutdown(self, how: int):
        return self.__socket.shutdown(how)

    def setsockopt(self, level: int, optname: int, value: typing.Union[int, bytes]):
        return self.__socket.setsockopt(level, optname, value)

class HTTPSocket(socket):
    responses = BaseHTTPRequestHandler.responses

    def _prepare_send_headers(self, 
                        data: str, 
                        content_type: str,
                        status: int, 
                        proto: int, 
                        hdrs: typing.Mapping[str, typing.Any]):

        msg, _ = self.responses.get(status)
        messages = [
            f'HTTP/{proto} {status} {msg}',
            f'Content-Length: {len(data)}'
        ]
        if data:
            messages.append(f'Content-Type: {content_type}')

        for key, value in hdrs.items():
            messages.append(f'{key}: {value}')

        return messages

    def _prepare_request_headers(self,
                                method: str,
                                path: str,
                                host: str,
                                protocol: int,
                                headers: typing.Mapping[str, typing.Any]):

        messages = [
            f'{method} {path} HTTP/{protocol}',
            f'Host: {host}'
        ]

        for key, value in headers.items():
            messages.append(f'{key}: {value}')

        return messages

    async def send(self, 
                data: typing.Union[str, typing.Dict]=..., 
                *, 
                status: int=...,
                content_type: str=...,
                protocol: int=...,
                headers: typing.Mapping[str, typing.Any]=...) -> int:

        self._check_closed()

        if data is not ...:
            if isinstance(data, dict):
                data = json.dumps(data)

        else:
            data = ''
        
        status = check_ellipsis(status, 200)
        content_type = check_ellipsis(content_type, 'text/plain')
        protocol = check_ellipsis(protocol, 1.1)
        headers = check_ellipsis(headers, {})

        messages = self._prepare_send_headers(
            data=data,
            content_type=content_type,
            status=status,
            proto=protocol,
            hdrs=headers
        )

        message = '\r\n'.join(messages)
        message += '\r\n\r\n'
        message += data

        return await self.raw_send(message.encode())

    async def raw_send(self, data: bytes):
        return await super().send(data)

    async def request(self, 
                    host: str, 
                    method: str=..., 
                    path: str=..., 
                    *,
                    protocol: int=..., 
                    headers: typing.Mapping[str, typing.Any]=...):

        self._check_closed()
        self._check_connected()

        method = check_ellipsis(method, 'GET')
        path = check_ellipsis(path, '/')
        protocol = check_ellipsis(protocol, 1.1)
        headers = check_ellipsis(headers, {})

        messages = self._prepare_request_headers(
            method=method,
            path=path,
            host=host,
            protocol=protocol,
            headers=headers
        )
        message = '\r\n'.join(messages)
        message += '\r\n\r\n'

        return await self.raw_send(message.encode())

    async def receive(self, nbytes: int=...) -> typing.Tuple[str, typing.Mapping[str, str], bytes]:
        self._check_closed()

        data = await super().recvall(nbytes)
        request = data.decode()

        headers = request.split('\r\n')
        body = headers[-1]
        
        info = headers[0]

        headers.remove(info)
        headers.remove(body)

        actual = {}
        method, path, protocol = info.split(' ')

        actual['method'] = method
        actual['path'] = path
        actual['protocol'] = protocol

        for header in headers:
            if not header:
                continue

            key, value = header.split(': ', maxsplit=1)
            actual[key] = value
        
        return body, actual, data

    async def accept(self, timeout: int=...) -> typing.Tuple['HTTPSocket', Address]:
        return await super().accept(timeout=timeout)

    def create_connection(self, host: str, port: int) -> HTTPConnectionContextManager:
        return HTTPConnectionContextManager(self, self._create_addr(host, port))

    def create_server(self, host: str, port: int, backlog: int=...) -> HTTPServerContextManager:
        return HTTPServerContextManager(self, self._create_addr(host, port), backlog)

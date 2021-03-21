import socket as _socket
import ssl as _ssl
import asyncio
import ipaddress
import concurrent.futures
import functools
from time import time
import typing

__all__ = (
    'is_ip',
    'create_connection',
    'create_server',
    'socket'
)

class _ConnectionContextManager:
    def __init__(self, __socket: 'socket', addr) -> None:
        self.socket = __socket
        self.addr = addr

    async def __aenter__(self):
        host, port = self.addr
        await self.socket.connect(host, port)

        return self.socket

    async def __aexit__(self, *args):
        self.socket.close()
        return self

class _ServerContextManager:
    def __init__(self, __socket: 'socket', addr, backlog) -> None:
        self.socket = __socket
        self.addr = addr
        self.backlog = backlog

    async def __aenter__(self):
        host, port = self.addr

        await self.socket.bind(host, port)
        await self.socket.listen(self.backlog)

        return self.socket

    async def __aexit__(self, _type, value, tb):
        print(_type, value, tb)
        if _type is _socket.timeout:
            return True



class InvalidAddress(Exception):
    ...

def is_ip(string: str):
    try:
        ipaddress.ip_address(string)
    except ValueError:
        return False

    return True

def create_connection(host: str, port: int, **kwargs):
    sock = socket(**kwargs)
    return _ConnectionContextManager(sock, (host, port))

def create_server(host: str, port: int, backlog: int=..., **kwargs):
    sock = socket(**kwargs)
    return _ServerContextManager(sock, (host, port), backlog)

class socket:
    def __init__(self,
                family: int = _socket.AF_INET,
                type: int = _socket.SOCK_STREAM,
                proto: int = 0, 
                fileno: int = ...,
                timeout: int = ...,
                *, 
                socket: _socket.socket = ..., 
                ssl: _ssl.SSLContext = ..., 
                loop: asyncio.AbstractEventLoop = ...,
                executor: concurrent.futures.Executor = ...) -> None:
        
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
            self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        else:
            self.__executor = executor
        
        self.timeout = 1 if timeout is ... else timeout
        self.__socket.settimeout(self.timeout)

    async def _run_in_executor(self, name: str, *args, **kwargs):
        method = getattr(self.__socket, name, None)
        if not method:
            method = getattr(_socket, name)

        executor = self.__executor
        partial = functools.partial(method, *args, **kwargs)

        result = await self._loop.run_in_executor(
            executor, partial
        )
        return result

    @property
    def ssl(self):
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

    async def gethostbyaddr(self, address: str) -> typing.Tuple[str, typing.List[str], typing.List[str]]:
        if not is_ip(address):
            raise InvalidAddress(address)

        host = await self._run_in_executor('gethostbyaddr', address)
        return host

    async def gethostbyname(self, name: str) -> str:
        info = await self._run_in_executor('gethostbyname', name)
        return info

    async def recv(self, nbytes: int=...) -> bytes:
        nbytes = 1024 if nbytes is ... else nbytes
        res = await self._run_in_executor('recv', nbytes)

        return res

    async def recvall(self, nbytes: int=...) -> bytes:
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

    async def send(self, data: typing.Union[bytes, str]) -> int:
        if isinstance(data, str):
            data = data.encode()

        res = await self._run_in_executor('send', data)
        return res

    async def connect(self, host: str, port: int) -> typing.NoReturn:
        if port == 443:
            self.__socket = self.__ssl.wrap_socket(self.__socket, server_hostname=host)

        if not is_ip(host):
            host = await self.gethostbyname(host)
            print(host)

        try:
            await self._run_in_executor('connect', (host, port))
        except _socket.timeout:
            raise ConnectionError('Could not connect to {0!r} on port {1!r}'.format(host, port)) from None

    async def bind(self, host: str, port: int) -> typing.NoReturn:
        if not is_ip(host):
            host = await self.gethostbyname(host)

        try:
            await self._run_in_executor('bind', (host, port))
        except _socket.timeout:
            raise ConnectionError('Could not bind to {0!r} on port {1!r}'.format(host, port)) from None

    async def accept(self, timeout: int=...) -> 'socket':
        timeout = 180 if timeout is ... else timeout
        self.__socket.settimeout(timeout)

        sock, addr = await self._run_in_executor('accept')
        new = self.__class__(
            socket=sock, 
            loop=self._loop, 
            executor=self.__executor, 
            ssl=self.__ssl
        )

        self.__socket.settimeout(self.timeout)
        return new

    async def listen(self, backlog: int=...) -> typing.NoReturn:
        if backlog is ...:
            backlog = 5

        await self._run_in_executor('listen', backlog)

    def create_connection(self, host: str, port: int):
        return _ConnectionContextManager(self.__socket, (host, port))

    def create_server(self, host: str, port: int, backlog: int=...):
        return _ServerContextManager(self.__socket, (host, port), backlog)

    def close(self) -> typing.NoReturn:
        self.__socket.close()
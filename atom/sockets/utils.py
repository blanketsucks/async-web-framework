import typing

if typing.TYPE_CHECKING:
    from .sockets import socket, Address
    from .websockets import Websocket

Generator = typing.Generator[str, None, None]

def iter_headers(headers: bytes) -> Generator:
    offset = 0

    while True:
        index = headers.index(b'\r\n', offset) + 2
        data = headers[offset:index]
        offset = index

        if data == b'\r\n':
            return

        yield [item.strip().decode() for item in data.split(b':', 1)]

def find_headers(data: bytes) -> typing.Tuple[Generator, str]:
    while True:
        end = data.find(b'\r\n\r\n') + 4

        if end != -1:
            headers = data[:end]
            body = data[end:]

            return iter_headers(headers), body

def check_ellipsis(__obj, __value):
    return __value if __obj is ... else __obj

_Websocket = typing.Generator[typing.Any, None, 'Websocket']
_socket = typing.Generator[typing.Any, None, 'socket']

class SocketContextManager:
    def __init__(self, __socket: 'socket', __addr: 'Address') -> None:
        self.socket = __socket

    async def __aenter__(self):
        return self.socket

    async def __aexit__(self, *args):
        self.socket.close()
        return self

class ConnectionContextManager(SocketContextManager):
    def __init__(self, __socket: 'socket', __addr: 'Address') -> None:
        self.socket = __socket
        self.addr = __addr

    async def __aenter__(self):
        host = self.addr.host
        port = self.addr.port

        await self.socket.connect(host, port)
        return self.socket

    def __await__(self) -> _socket:
        return self.__aenter__().__await__()

    __iter__ = __await__

class WSConnectionContextManager(ConnectionContextManager):
    def __init__(self, __socket: 'Websocket', __addr: 'Address') -> None:
        self.socket = __socket
        self.addr = __addr

    async def __aenter__(self) -> 'Websocket':
        return await super().__aenter__()

    async def __aexit__(self, *args):
        await self.socket.close()
        return self

    def __await__(self) -> _Websocket:
        return super().__await__()

class ServerContextManager(SocketContextManager):
    def __init__(self, __socket: 'socket', __addr: 'Address', __backlog: int) -> None:
        self.socket = __socket
        self.addr = __addr
        self.backlog = __backlog

    async def __aenter__(self):
        host = self.addr.host
        port = self.addr.port

        await self.socket.bind(host, port)
        await self.socket.listen(self.backlog)

        return self.socket

    def __await__(self) -> _socket:
        return self.__aenter__().__await__()

    __iter__ = __await__


class WSServerContextManager(ServerContextManager):
    def __init__(self, __socket: 'Websocket', __addr: 'Address', __backlog: int) -> None:
        self.socket = __socket
        self.addr = __addr
        self.backlog = __backlog

    async def __aenter__(self) -> 'Websocket':
        return await super().__aenter__()

    async def __aexit__(self, *args):
        await self.socket.close()
        return self

    def __await__(self) -> _Websocket:
        return super().__await__()


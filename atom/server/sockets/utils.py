import typing

if typing.TYPE_CHECKING:
    from .sockets import socket, Address, HTTPSocket
    from .websockets import Websocket

def check_ellipsis(__obj, __value):
    return __value if __obj is ... else __obj

_Websocket = typing.Generator[typing.Any, None, 'Websocket']
_socket = typing.Generator[typing.Any, None, 'socket']
_HTTPSocket = typing.Generator[typing.Any, None, 'HTTPSocket']

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

class HTTPConnectionContextManager(ConnectionContextManager):
    def __init__(self, __socket: 'HTTPSocket', __addr: 'Address') -> None:
        self.socket = __socket
        self.addr = __addr

    async def __aenter__(self) -> 'HTTPSocket':
        return await super().__aenter__()

    def __await__(self) -> _HTTPSocket:
        return super().__await__()

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

class HTTPServerContextManager(ServerContextManager):
    def __init__(self, __socket: 'HTTPSocket', __addr: 'Address', __backlog: int) -> None:
        self.socket = __socket
        self.addr = __addr
        self.backlog = __backlog

    async def __aenter__(self) -> 'HTTPSocket':
        return await super().__aenter__()

    def __await__(self) -> _HTTPSocket:
        return super().__await__()

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


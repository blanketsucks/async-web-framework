from .bases import Connection
from . import sockets

import typing
from http.server import BaseHTTPRequestHandler
import asyncio

if typing.TYPE_CHECKING:
    from .protocol import HTTPProtocol
    from .transport import HTTPTransport

__all__ = (
    'HTTPConnection',
)


class HTTPConnection(Connection):
    version = 1.1
    responses = BaseHTTPRequestHandler.responses

    def __init__(self, 
                loop: asyncio.AbstractEventLoop, 
                protocol: 'HTTPProtocol', 
                transport: 'HTTPTransport', 
                socket: sockets.socket, 
                address: sockets.Address, 
                peername: sockets.Address, 
                sockname: sockets.Address) -> None:
        
        self.loop = loop
        self.protocol = protocol

        self.__extra = {

        }


    async def write(self,
                    status: int = ...,
                    *,
                    body: typing.Union[str, typing.Dict, typing.List, typing.Any] = ...,
                    content_type: str = ...,
                    headers: typing.Dict = ...):

        body = sockets.check_ellipsis(body, '')

        if isinstance(body, (dict, list)):
            content_type = 'application/json'

        socket: sockets.HTTPSocket = self.get_info('socket')
        await socket.send(
            data=body,
            status=status,
            content_type=content_type,
            headers=headers,
            protocol=self.version
        )

    async def writefile(self, filename: str, *, offset: int = 0, fallback: bool = ...):
        socket: sockets.socket = self.get_info('socket')
        loop: asyncio.AbstractEventLoop = self.get_info('loop')

        with open(filename, 'rb') as file:
            result = await loop.sock_sendfile(
                socket=socket,
                file=file,
                offset=offset,
                fallback=fallback
            )

        return result

    async def getaddrinfo(self,
                          host: str = ...,
                          port: typing.Union[int, str] = ...,
                          *,
                          family: int = ...,
                          type: int = ...,
                          proto: int = ...,
                          flags: int = ...):

        loop: asyncio.AbstractEventLoop = self.get_info('loop')
        res = await loop.getaddrinfo(
            host=host,
            port=port,
            family=family,
            type=type,
            proto=proto,
            flags=flags
        )

        return res

    async def getnameinfo(self, host: str = ..., port: int = ..., *, flags: int = ...):
        host = '127.0.0.1' if host is ... else host
        port = 8080 if port is ... else port

        addr = (host, port)
        loop: asyncio.AbstractEventLoop = self.get_info('loop')

        res = await loop.getnameinfo(
            sockaddr=addr,
            flags=flags
        )
        return res

    def close(self):
        socket = self.get_info('socket')
        socket.close()

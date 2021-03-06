
import asyncio
from .bases import Connection

import typing
from http.server import BaseHTTPRequestHandler
import socket as sockets

if typing.TYPE_CHECKING:
    from .transport import HTTPTransport
    
__all__ = (
    'HTTPConnection',
)

class HTTPConnection(Connection):
    version = '1.1'
    responses = BaseHTTPRequestHandler.responses

    def __init__(self, info: typing.Dict) -> None:
        self._info = info

    def get_info(self, name: str):
        item = self._info.get(name)
        return item

    async def write(self, 
                    status: int=..., 
                    *, 
                    body: typing.Union[str, typing.Dict, typing.List, typing.Any]=..., 
                    content_type: str=...,
                    headers: typing.Dict=...):

        status = 200 if status is Ellipsis else status
        content_type = 'text/plain' if content_type is Ellipsis else content_type
        body = 'No content.' if body is Ellipsis else body
        headers = {} if headers is Ellipsis else headers

        if isinstance(body, (dict, list)):
            content_type = 'application/json'

        status_msg, _ = self.responses.get(status)
        
        messages = [
            f"HTTP/{self.version} {status} {status_msg}",
            f"Content-Type: {content_type}",
            f"Content-Length: {len(body)}",
        ]

        if headers:
            for header, value in headers.items():
                messages.append(f"{header}: {value}")

        if body is not None:
            messages.append("\r\n" + body)

        socket: sockets.socket = self.get_info('socket')
        transport: 'HTTPTransport' = self.get_info('transport')
        loop: asyncio.AbstractEventLoop = self.get_info('loop')

        message = '\r\n'.join(messages)
        print(message)
        
        encoded = message.encode('utf-8')

        await transport.call_protocol('socket_sent', encoded)
        await loop.sock_sendall(socket, encoded)
        
    async def writeraw(self, data: bytes):
        socket: sockets.socket = self.get_info('socket')
        transport: 'HTTPTransport' = self.get_info('transport')
        loop: asyncio.AbstractEventLoop = self.get_info('loop')

        await transport.call_protocol('socket_sent', data)
        await loop.sock_sendall(socket, data)

    async def writefile(self, filename: str, *, offset: int=0, fallback: bool=...):
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
                        host: str=..., 
                        port: typing.Union[int, str]=..., 
                        *, 
                        family: int=...,
                        type: int=...,
                        proto: int=...,
                        flags: int=...):

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

    async def getnameinfo(self, host: str=..., port: int=..., *, flags: int=...):
        host = '127.0.0.1' if host is Ellipsis else host
        port = 8080 if port is Ellipsis else port

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

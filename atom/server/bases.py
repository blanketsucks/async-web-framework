import typing
import asyncio

import socket as _socket

__all__ = (
    'Protocol',
    'Connection',
    'Server'
)

class Protocol:
    def __init__(self, loop: asyncio.AbstractEventLoop=...) -> None:
        ...

    async def on_connection_made(self, connection: 'Connection'):
        ...

    async def on_socket_receive(self, data: bytes):
        ...

    async def on_socket_sent(self, data: bytes):
        ...

    async def on_error(self, exc: Exception):
        ...

class Transport:
    def __init__(self, socket: _socket.socket, loop: asyncio.AbstractEventLoop, protocol: Protocol) -> None:
        ...
    
    async def call_protocol(self, name: str, *args):
        ...

    async def listen(self):
        ...

    async def handle(self):
        ...

class Connection:
    def __init__(self, info: typing.Dict) -> None:
        ...

    def get_info(self, name: str):
        ...

    async def write(self, body: bytes):
        ...

    async def writefile(self, filename: str, *, offset: int=..., fallback: bool=...):
        ...

    async def getaddrinfo(self, 
                        host: str=..., 
                        port: typing.Union[int, str]=..., 
                        *, 
                        family: int=...,
                        type: int=...,
                        proto: int=...,
                        flags: int=...):
        ...

    async def getnameinfo(self, host: str=..., port: int=..., *, flags: int=...):  
        ...

    def close(self):
        ...

class Server:
    def __init__(self, 
                protocol: Protocol, 
                host: str=..., 
                port: int=...,
                *,
                loop: asyncio.AbstractEventLoop=...) -> None:
        ...

    async def serve(self):
        ...

    def close(self):
        ...

import typing
import asyncio

from . import sockets

__all__ = (
    'Protocol',
    'Connection',
    'Server',
    'Transport'
)

class Protocol:
    def __init__(self, loop: asyncio.AbstractEventLoop=...) -> None:
        ...

    async def on_connection_made(self, connection: 'Connection'):
        ...

    async def on_connection_lost(self, exc: typing.Optional[Exception]):
        ...

    async def on_data_receive(self, data: bytes):
        ...



class Transport:
    def __init__(self, socket: sockets.socket, loop: asyncio.AbstractEventLoop, protocol: Protocol) -> None:
        ...
    
    async def call_protocol(self, name: str, *args):
        ...

    async def listen(self):
        ...

    async def handle(self):
        ...

class Connection:
    def __init__(self, 
                loop: asyncio.AbstractEventLoop, 
                protocol: Protocol, 
                transport: Transport, 
                socket: sockets.socket, 
                address: sockets.Address, 
                peername: sockets.Address, 
                sockname: sockets.Address) -> None:
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

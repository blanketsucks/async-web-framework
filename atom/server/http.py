import typing
from .bases import Server
from .transport import HTTPTransport
from .protocol import HTTPProtocol, WebsocketProtocol
from .errors import ConnectionError
from .sockets import HTTPSocket, Websocket
from atom.datastructures import URL

from .bases import Protocol

import asyncio

__all__ = (
    'HTTPServer',
)

class HTTPServer(Server):
    def __init__(self, 
                protocol: HTTPProtocol, 
                host: str, 
                port: int, 
                *, 
                loop: asyncio.AbstractEventLoop) -> None:
        self.protocol = protocol
        self.loop = loop

        self.host = host
        self.port = port

    async def serve(self):
        # self.socket = HTTPSocket(socket.AF_INET, socket.SOCK_STREAM, loop=self.loop)
        # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            await self.socket.bind(self.host, self.port)
        except Exception as exc:
            self.close()
            raise ConnectionError() from exc

        self.transport = transport = HTTPTransport(
            self.socket, self.loop, self.protocol
        )
        print(transport)
        await transport.listen()

    def close(self): ...
        # self.socket.shutdown(socket.SHUT_RDWR)
        
async def create_server(
    protocol: typing.Type[HTTPProtocol],
    host: str='127.0.0.1',
    port: int=8080,
    *,
    loop: asyncio.AbstractEventLoop=...
):

    if loop is ...:
        loop = asyncio.get_event_loop()

async def create_connection(
    protocol: typing.Type[Protocol],
    host: typing.Union[bytes, str],
    port: int=...
):
    if isinstance(host, bytes):
        host = host.decode()


async def _handle_websocket_connection(socket: Websocket, protocol: WebsocketProtocol):
    ...

async def _handle_http_connection(socket: HTTPSocket, protocol: HTTPProtocol):
    ...
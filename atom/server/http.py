from .bases import Server
from .transport import HTTPTransport
from .protocol import HTTPProtocol

import asyncio
import socket
import sys

__all__ = (
    'HTTPServer'
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
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.socket.bind((self.host, self.port))
        except Exception as exc:
            
            await self.close()
            sys.exit(1)

        self.transport = transport = HTTPTransport(
            self.socket, self.loop, self.protocol
        )

        await transport.listen()

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)


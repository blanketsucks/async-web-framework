import ssl
from .bases import Server
from .transport import HTTPTransport
from .protocol import HTTPProtocol
from .errors import ConnectionError

import asyncio
import socket
import sys

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
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.socket.bind((self.host, self.port))
        except Exception as exc:
            self.close()
            raise ConnectionError() from exc

        self.transport = transport = HTTPTransport(
            self.socket, self.loop, self.protocol
        )

        await transport.listen()

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.close()
        

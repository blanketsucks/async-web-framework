from atom.server import HTTPConnection, HTTPTransport, HTTPServer, HTTPProtocol
from .errors import InvalidHandshake, WebsocketError
from .websocket import MAGIC, Websocket

import hashlib
import base64
import typing
import asyncio
import sys
import socket as sockets

__all__ = (
    'WebsocketConnection',
    'WebsocketProtocol',
    'WebsocketTransport',
    'WebsocketServer'
)


class WebsocketConnection(HTTPConnection):
    def build_key(self, key: str) -> str:
        sha1 = hashlib.sha1((key + MAGIC).encode()).digest()
        return base64.b64encode(sha1).decode()

    def check_request(self):
        key = None
        protocol = self.get_info('protocol')

        for header, item in protocol.request.headers.items():
            print(header, item)
            if header == "Sec-WebSocket-Key":
                key = item

        if not key:
            raise InvalidHandshake(key=True)

        return key

    async def handshake(self):
        key = self.check_request()        
        key = self.build_key(key)

        headers = {}

        headers['Upgrade'] = 'websocket'
        headers['Connection'] = 'Upgrade'
        headers['Sec-WebSocket-Accept'] = key

        messages = [
            f"HTTP/{self.version} 101 Switching Protocols",
        ]

        for header, value in headers.items():
            messages.append(f"{header}: {value}")

        message = '\r\n'.join(messages)
        await self.writeraw(message.encode())

        sock = self.get_info('socket')
        loop = self.get_info('loop')

        return Websocket(
            sock, loop
        )

class WebsocketProtocol(HTTPProtocol):
    async def on_socket_receive(self, data: bytes):
        await self.parse_request(data)


class WebsocketTransport(HTTPTransport):
    def __init__(self, socket: sockets.socket, loop: asyncio.AbstractEventLoop, protocol: WebsocketProtocol) -> None:
        if not isinstance(protocol, WebsocketProtocol):
            fmt = 'Expected WebsocketProtocol but got {0.__class__.__name__} instead'
            raise WebsocketError(fmt.format(protocol))

        super().__init__(socket, loop, protocol)

    async def listen(self):
        self.socket.listen(5)

        while True:
            client, address = await self.loop.sock_accept(self.socket)

            self.clients.append(client)
            client.settimeout(60)

            info = {
                'loop': self.loop,
                'socket': client,
                'transport': self,
                'protocol': self.protocol
            }

            conn = WebsocketConnection(info)
            await self.call_protocol('connection_made', conn)

            task = self.loop.create_task(
                self.handle(client, address)
            )
            self.client_tasks.append(task)


class WebsocketServer(HTTPServer):
    async def serve(self):
        self.socket = sockets.socket(sockets.AF_INET, sockets.SOCK_STREAM)

        try:
            self.socket.bind((self.host, self.port))
        except Exception as e:
            await self.close()
            sys.exit(1)

        self.transport = transport = WebsocketTransport(
            self.socket, self.loop, self.protocol
        )

        await transport.listen()

from .sockets import socket as sockets
from .websockets import Websocket

import socket

__all__ = (
    'Connection',
    'WebsocketConnection'
)

class Connection:
    def __init__(self, __socket: sockets) -> None:
        self._socket = __socket

        self._closed = False

    @property
    def socket(self):
        return self._socket

    @property
    def peername(self):
        return self._socket.raddr

    @property
    def sockname(self):
        return self._socket.laddr

    @property
    def is_closed(self):
        return self._closed

    async def write(self, data):
        return await self._socket.send(data)

    async def sendfile(self, file, *, offset=0, count=None):
        return await self._socket.sendfile(file, offset=offset, count=count)

    async def recv(self):
        return await self._socket.recv(32768)

    async def recvfrom(self):
        return await self._socket.recvfrom(32768)

    async def recv_into(self, buffer, nbytes=None):
        return await self._socket.recv_into(buffer, nbytes)

    async def recvfrom_into(self, buffer, nbytes=None):
        return await self._socket.recvfrom_into(buffer, nbytes)

    def close(self):
        self._socket.close()
        self._closed = True

    def shutdown(self):
        self.close()
        self._socket.shutdown(socket.SHUT_RDWR)

class WebsocketConnection:
    def __init__(self, socket: Websocket) -> None:
        self._socket = socket

        self.state = self._socket.state
        self._closed = False

    @property
    def socket(self):
        return self._socket

    @property
    def peername(self):
        return self._socket.raddr

    @property
    def sockname(self):
        return self._socket.laddr

    @property
    def is_closed(self):
        return self._closed

    async def handshake(self):
        await self._socket.handshake()

    async def write(self, data: bytes):
        return await self._socket.send(data)

    async def ping(self, data=None):
        await self._socket.ping(data)

    async def pong(self, data=None):
        await self._socket.pong(data)

    async def binary(self, data=None):
        await self._socket.send_binary(data)

    async def continuation(self, data=None):
        await self._socket.continuation(data)

    async def send_bytes(self, data=None, *, opcode=None):
        await self._socket.send_bytes(data, opcode)

    async def send_str(self, data=None, *, opcode=None):
        await self._socket.send_str(data, opcode)

    async def send_json(self, data=None, *, opcode=None):
        await self._socket.send_json(data, opcode)

    async def receive(self):
        data = await self._socket.receive()
        return data

    async def receive_bytes(self):
        data = await self._socket.receive_bytes()
        return data

    async def receive_str(self):
        data = await self._socket.receive_str()
        return data

    async def receive_json(self):
        data = await self._socket.receive_json()
        return data

    async def close(self, data=None, code=None):
        await self._socket.close(code=code, data=data)
        self.shutdown()

    def shutdown(self):
        self._socket.close()
        self._socket.shutdown(socket.SHUT_RDWR)

        self._closed = True
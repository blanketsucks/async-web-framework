from .sockets import socket as sockets
from .websockets import Websocket
from .enums import WebSocketCloseCode, WebSocketOpcode

import typing
import socket
import warnings

__all__ = (
    'Connection',
    'WebsocketConnection'
)

class Connection:
    def __init__(self, __socket: sockets) -> None:
        self._socket = __socket

        self._closed = False

    def __del__(self):
        if not self._closed:
            warnings.simplefilter('always', ResourceWarning)
            warnings.warn(
                message=f'Unclosed connection {self!r}',
                category=ResourceWarning,
            )

            warnings.simplefilter('default', ResourceWarning)

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

    async def write(self, data: bytes):
        return await self._socket.send(data)

    async def sendfile(self, file: typing.IO[bytes], *, offset: int = ..., count: int = ...):
        return await self._socket.sendfile(file, offset=offset, count=count)

    async def recv(self):
        return await self._socket.recv(32768)

    async def recvfrom(self):
        return await self._socket.recvfrom(32768)

    async def recv_into(self, buffer: bytearray=..., nbytes: int=...):
        if nbytes is ...:
            nbytes = 32768

        if buffer is ...:
            buffer = bytearray(nbytes)

        return await self._socket.recv_into(buffer, nbytes)

    async def recvfrom_into(self, buffer: bytearray=..., nbytes: int=...):
        if nbytes is ...:
            nbytes = 32768

        if buffer is ...:
            buffer = bytearray(nbytes)

        return await self._socket.recvfrom_into(buffer, nbytes)

    def close(self):
        self._socket.close()
        self._closed = True

    def shutdown(self):
        self.close()
        self._socket.shutdown(socket.SHUT_RDWR)

class WebsocketConnection(Connection):
    def __init__(self, socket: Websocket) -> None:
        self._socket = socket

    async def handshake(self):
        await self._socket.handshake()

    async def ping(self, data: bytes=...):
        await self._socket.ping(data)

    async def pong(self, data: bytes=...):
        await self._socket.pong(data)

    async def binary(self, data: bytes=...):
        await self._socket.send_binary(data)

    async def continuation(self, data: bytes=...):
        await self._socket.continuation(data)

    async def send_bytes(self, data: bytes=..., *, opcode: WebSocketOpcode=...):
        await self._socket.send_bytes(data, opcode)

    async def send_str(self, data: str=..., *, opcode: WebSocketOpcode=...):
        await self._socket.send_str(data, opcode)

    async def send_json(self, data: typing.Dict[str, typing.Any]=..., *, opcode: WebSocketOpcode=...):
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

    async def close(self, data: bytes=..., code: WebSocketCloseCode=...):
        await self._socket.close(code=code, data=data)
        self.shutdown()

    def shutdown(self):
        self._socket._close()
        self._socket.shutdown(socket.SHUT_RDWR)

        self._closed = True
import asyncio
import typing
import json
import socket
import collections

from .frame import WebSocketFrame, WebSocketOpcode, Data

class _socket:
    def __init__(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        
        self.loop: asyncio.AbstractEventLoop = transport.get_protocol().loop
        self.__socket: socket.socket = transport.get_extra_info('socket')._sock

    async def send(self, data: bytes):
        return await self.loop.sock_sendall(self.__socket, data)

    async def recv(self, nbytes: int):
        return await self.loop.sock_recv(self.__socket, nbytes)

class Websocket:
    def __init__(self, transport: asyncio.Transport, reader: asyncio.StreamReader) -> None:
        self.transport = transport
        self.queue = asyncio.Queue(maxsize=364)

        self.__socket = _socket(transport)

    def feed_data(self, data: bytes):
        self.queue.put_nowait(data)

    def send_frame(self, frame: WebSocketFrame):
        data = frame.encode()
        return self.transport.write(data)

    def send_bytes(self, data: bytes, *, opcode: WebSocketOpcode=None):
        if not opcode:
            opcode = WebSocketOpcode.TEXT

        frame = WebSocketFrame(opcode=opcode, data=data)
        return self.send_frame(frame)

    def send_str(self, data: str, *, opcode: WebSocketOpcode=None):
        if not opcode:
            opcode = WebSocketOpcode.TEXT

        return self.send_bytes(data.encode(), opcode=opcode)

    def send_json(self, data: typing.Dict, *, opcode: WebSocketOpcode=None):
        if not opcode:
            opcode = WebSocketOpcode.TEXT

        return self.send_str(json.dumps(data), opcode=opcode)

    async def receive(self):
        return await self.queue.get()

    async def receive_bytes(self):
        data, opcode = await self.receive()
        return data.data, opcode

    async def receive_str(self):
        data, opcode = await self.receive()
        return data.as_string(), opcode

    async def receive_json(self):
        data, opcode = await self.receive()
        return data.as_json(), opcode

        
    
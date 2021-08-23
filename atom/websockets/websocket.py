from typing import TYPE_CHECKING, Tuple, Dict
import asyncio
import json

from .frame import WebSocketFrame, WebSocketOpcode, Data, WebSocketCloseCode
from atom.server import ClientConnection

if TYPE_CHECKING:
    from atom.protocol import ApplicationProtocol, Connection

class Websocket:
    def __init__(self, connection: ClientConnection) -> None:
        self.connection = connection
        self.peer = connection.peername

        self._closed = False

    def is_closed(self):
        return self._closed

    def feed_data(self, data: bytes):
        return self.connection._reader.feed_data(data)

    async def send_frame(self, frame: WebSocketFrame):
        data = frame.encode()
        await self.connection.write(data)

        return len(data)

    async def send_bytes(self, data: bytes, *, opcode: WebSocketOpcode=None):
        if not opcode:
            opcode = WebSocketOpcode.TEXT

        frame = WebSocketFrame(opcode=opcode, data=data)
        return await self.send_frame(frame)

    async def send_str(self, data: str, *, opcode: WebSocketOpcode=None):
        return await self.send_bytes(data.encode(), opcode=opcode)

    async def send_json(self, data: Dict, *, opcode: WebSocketOpcode=None):
        return await self.send_str(json.dumps(data), opcode=opcode)

    async def ping(self, data: bytes):
        await self.send_bytes(data, opcode=WebSocketOpcode.PING)

    async def pong(self, data: bytes):
        return await self.send_bytes(data, opcode=WebSocketOpcode.PONG)

    async def continuation(self, data: bytes):
        return await self.send_bytes(data, opcode=WebSocketOpcode.CONTINUATION)

    async def binary(self, data: bytes):
        return await self.send_bytes(data, opcode=WebSocketOpcode.BINARY)

    async def close(self, data: bytes, code: WebSocketCloseCode=None):
        if not code:
            code = WebSocketCloseCode.NORMAL

        code = code.to_bytes(2, 'big', signed=False)
        frame = WebSocketFrame(opcode=WebSocketOpcode.CLOSE, data=code + data)

        self._closed = True
        len = await self.send_frame(frame)

        self.connection.close()
        return len

    async def receive(self):
        opcode, raw, data = await WebSocketFrame.decode(self.connection.read)
        return Data(raw, data), opcode

    async def receive_bytes(self):
        data, opcode = await self.receive()
        return data.data, opcode

    async def receive_str(self):
        data, opcode = await self.receive()
        return data.as_string(), opcode

    async def receive_json(self):
        data, opcode = await self.receive()
        return data.as_json(), opcode

        
    
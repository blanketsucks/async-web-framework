import asyncio
import typing
import json

from .frame import WebsocketFrame, WebsocketOpcode, Data, WebsocketCloseCode

class Websocket:
    def __init__(self, transport: asyncio.Transport, peer: typing.Tuple[str, int]) -> None:
        self.transport = transport
        self.peer = peer
        self.protocol = transport.get_protocol()

        self.reader = asyncio.StreamReader()
        self.closed = False

    def send_frame(self, frame: WebsocketFrame, mask: bool=True):
        data = frame.encode(masked=mask)
        self.transport.write(data)

        return len(data)

    def send_bytes(self, data: bytes, *, opcode: WebsocketOpcode=None, mask: bool=True):
        if not opcode:
            opcode = WebsocketOpcode.TEXT

        frame = WebsocketFrame(opcode=opcode, data=data)
        return self.send_frame(frame, mask)

    def send_str(self, data: str, *, opcode: WebsocketOpcode=None):
        return self.send_bytes(data.encode(), opcode=opcode)

    def send_json(self, data: typing.Dict, *, opcode: WebsocketOpcode=None):
        return self.send_str(json.dumps(data), opcode=opcode)

    def ping(self, data: bytes):
        return self.send_bytes(data, opcode=WebsocketOpcode.PING)

    def pong(self, data: bytes):
        return self.send_bytes(data, opcode=WebsocketOpcode.PONG)

    def continuation(self, data: bytes):
        return self.send_bytes(data, opcode=WebsocketOpcode.CONTINUATION)

    def binary(self, data: bytes):
        return self.send_bytes(data, opcode=WebsocketOpcode.BINARY)

    def close(self, data: bytes, code: WebsocketCloseCode=None):
        if not code:
            code = WebsocketCloseCode.NORMAL

        code = code.to_bytes(2, 'big', signed=False)
        frame = WebsocketFrame(opcode=WebsocketOpcode.CLOSE, data=code + data)

        self.closed = True
        len = self.send_frame(frame)

        self.transport.close()
        return len

    async def receive(self, *, mask: bool=False):
        opcode, raw, data = await WebsocketFrame.decode(self.reader.readexactly, masked=mask)
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

        
    
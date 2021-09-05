from typing import Any, Dict, Tuple, Optional
import json

from .frame import WebSocketFrame, WebSocketOpcode, Data, WebSocketCloseCode
from railway.stream import StreamReader, StreamWriter

__all__ = (
    'ServerWebsocket',
    'ClientWebsocket',
)

class ServerWebsocket:
    def __init__(self, reader: StreamReader, writer: StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

        self.peername: Tuple[str, int] = self._writer.get_extra_info('peername')
        self._closed = False

    def __repr__(self) -> str:
        return f'<Websocket peername={self.peername}>'

    def is_closed(self):
        return self._closed

    def feed_data(self, data: bytes):
        return self._reader.feed_data(data)

    async def send_frame(self, frame: WebSocketFrame):
        data = frame.encode()
        await self._writer.write(data)

        return len(data)

    async def send_bytes(self, data: bytes, *, opcode: Optional[WebSocketOpcode]=None):
        if not opcode:
            opcode = WebSocketOpcode.TEXT

        frame = WebSocketFrame(opcode=opcode, data=data)
        return await self.send_frame(frame)

    async def send(self, data: bytes, *, opcode: Optional[WebSocketOpcode]=None):
        return await self.send_bytes(data, opcode=opcode)

    async def send_str(self, data: str, *, opcode: Optional[WebSocketOpcode]=None):
        return await self.send_bytes(data.encode(), opcode=opcode)

    async def send_json(self, data: Dict[str, Any], *, opcode: Optional[WebSocketOpcode]=None):
        return await self.send_str(json.dumps(data), opcode=opcode)

    async def ping(self, data: bytes):
        await self.send_bytes(data, opcode=WebSocketOpcode.PING)

    async def pong(self, data: bytes):
        return await self.send_bytes(data, opcode=WebSocketOpcode.PONG)

    async def continuation(self, data: bytes):
        return await self.send_bytes(data, opcode=WebSocketOpcode.CONTINUATION)

    async def binary(self, data: bytes):
        return await self.send_bytes(data, opcode=WebSocketOpcode.BINARY)

    async def close(self, data: bytes, code: Optional[WebSocketCloseCode]=None) -> None:
        if not code:
            code = WebSocketCloseCode.NORMAL

        close = code.to_bytes(2, 'big', signed=False) # type: ignore
        frame = WebSocketFrame(opcode=WebSocketOpcode.CLOSE, data=close + data)

        self._closed = True
        await self.send_frame(frame)

        self._writer.close()     

    async def receive(self):
        opcode, raw, data = await WebSocketFrame.decode(self._reader.read)
        return Data(raw, data)

    async def receive_bytes(self):
        data = await self.receive()
        return data.data

    async def receive_str(self):
        data = await self.receive()
        return data.as_string()

    async def receive_json(self):
        data = await self.receive()
        return data.as_json()

class ClientWebsocket(ServerWebsocket):

    async def send_frame(self, frame: WebSocketFrame):
        data = frame.encode(masked=True)
        await self._writer.write(data)

        return len(data)

    async def receive(self):
        opcode, raw, data = await WebSocketFrame.decode(self._reader.read, masked=False)
        return Data(raw, data)
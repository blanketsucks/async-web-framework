import asyncio
import typing
import json

from .frame import WebSocketFrame, WebSocketOpcode, Data

if typing.TYPE_CHECKING:
    from atom.protocol import ApplicationProtocol

class Websocket:
    def __init__(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self.protocol: 'ApplicationProtocol' = transport.get_protocol()

        self.reader = asyncio.StreamReader()
        self.queue = asyncio.Queue()

        self._ping_waiter: typing.Optional[asyncio.Future] = None

    def feed_data(self, data: bytes):
        self.queue.put_nowait(data)
        opcode = WebSocketFrame.get_opcode(data)

        if opcode is WebSocketOpcode.PONG and self._ping_waiter is not None:
            self._ping_waiter.set_result(None)

    def send_frame(self, frame: WebSocketFrame):
        data = frame.encode()
        self.transport.write(data)

        return len(data)

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

    def ping(self, data: bytes) -> asyncio.Future[None]:
        self.send_bytes(data, opcode=WebSocketOpcode.PING)
        self._ping_waiter = self.protocol.loop.create_future()
        
        return self._ping_waiter

    def pong(self, data: bytes):
        return self.send_bytes(data, opcode=WebSocketOpcode.PONG)

    async def receive(self):
        data = await self.queue.get()
        self.reader.feed_data(data)

        opcode, raw, data = await WebSocketFrame.decode(self.reader.readexactly)
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

        
    
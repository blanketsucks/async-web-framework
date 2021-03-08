import asyncio
import socket
import enum
import struct

class OPCode(enum.Enum):
	CONTINUATION = 0x0
	TEXT = 0x1
	BINARY = 0x2
	CLOSE = 0x8
	PING = 0x9
	PONG = 0xA

class WebsocketFrame:
    def __init__(self, loop: asyncio.AbstractEventLoop, socket: socket.socket) -> None:
        self.loop = loop
        self.socket = socket

    def decode(self, payload: bytes, opcode: OPCode):
        if opcode is OPCode.TEXT:
            return payload.decode('utf-8')

        if opcode is OPCode.BINARY:
            return payload

        return None

    async def recv(self, nbytes: int):
        data = bytearray()
        while len(data) < nbytes:
            data += await self.loop.sock_recv(self.socket, nbytes - len(data))

        return data

    async def read(self):
        bytesarray = await self.recv(1)
        byte = bytesarray[0]

        self.fin = bool(byte >> 7 & 0b1)
        self.opcode = OPCode(byte & 0b00001111)

        bytesarray = await self.recv(1)
        byte = bytesarray[0]

        self.mask = bool(byte >> 7 & 0b1)
        self.payload_lenght = OPCode(byte & 0b01111111)
        
        if not self.mask:
            return None

        if self.payload_len == 126:
            data = await self.recv(2)
            self.payload_len = struct.unpack(">H", data)[0]

            print(self.payload_len)

        elif self.payload_len == 127:
            data = await self.recv(4)
            self.payload_len = struct.unpack(">I", data)[0]

        data = await self.recv(4)
        self.mask_key = data

        decoded_bytes = bytearray()

        for i in range(self.payload_len):
            byte = await self.recv(1)[0]
            decoded_bytes.append(byte ^ (self.mask_key[i % 4] & 0xFF))

        self.payload = decoded_bytes
        return self
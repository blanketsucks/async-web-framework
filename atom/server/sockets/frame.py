import struct
import typing
import os
import json

from .enums import WebSocketOpcode

if typing.TYPE_CHECKING:
    from .websockets import Websocket

__all__ = (
    'mask',
    'Data',
    'WebSocketFrame'
)

def mask(data: typing.ByteString, mask: bytes) -> bytearray:
    data = bytearray(data)

    for i in range(len(data)):
        data[i] ^= mask[i % 4]

    return bytes(data)

class Data:
    def __init__(self, raw: bytearray, frame: 'WebSocketFrame') -> None:
        self.raw = raw
        self._frame = frame

    @property
    def opcode(self):
        return self._frame.opcode

    @property
    def data(self):
        return self._frame.data

    @property
    def frame(self):
        return self._frame

    def encode(self, opcode: WebSocketOpcode=..., *, masked: bool=...):
        frame = WebSocketFrame(
            opcode=WebSocketOpcode.TEXT if opcode is ... else opcode,
            data=self.data
        )   

        masked = False if masked is ... else masked
        return frame.encode(masked)

    def as_string(self):
        return self.data.decode()

    def as_json(self) -> typing.Dict:
        string = self.as_string()
        return json.loads(string)

class WebSocketFrame:
    SHORT_LENGTH = struct.Struct('!H')
    LONGLONG_LENGTH = struct.Struct('!Q')

    def __init__(self, *, 
                opcode: WebSocketOpcode, 
                fin: bool=True,
                rsv1: bool=False, 
                rsv2: bool=False, 
                rsv3: bool=False,
                data: bytes):

        self.opcode = opcode
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.data = data

    def __repr__(self) -> str:
        attrs = ('fin', 'rsv1', 'rsv2', 'rsv3', 'opcode')
        s = ', '.join(f'{name}={getattr(self, name)!r}' for name in attrs)
        return f'<{self.__class__.__name__} {s}>'

    @staticmethod
    def mask(data: typing.ByteString, mask: bytes) -> bytearray:
        data = bytearray(data)

        for i in range(len(data)):
            data[i] ^= mask[i % 4]

        return bytes(data)

    def encode(self, masked: bool = False) -> bytearray:
        buffer = bytearray(2)
        buffer[0] = ((self.fin << 7)
                     | (self.rsv1 << 6)
                     | (self.rsv2 << 5)
                     | (self.rsv3 << 4)
                     | self.opcode)
        buffer[1] = masked << 7

        length = len(self.data)
        if length < 126:
            buffer[1] |= length
        elif length < 2 ** 16:
            buffer[1] |= 126
            buffer.extend(self.SHORT_LENGTH.pack(length))
        else:
            buffer[1] |= 127
            buffer.extend(self.LONGLONG_LENGTH.pack(length))

        if masked:
            mask_bytes = os.urandom(4)
            buffer.extend(mask_bytes)
            data = self.mask(self.data, mask_bytes)

        else:
            data = self.data

        buffer.extend(data)
        return buffer

    @classmethod
    async def decode(cls, socket: 'Websocket') -> typing.Tuple[WebSocketOpcode, bytearray, 'WebSocketFrame']:
        raw = bytearray()

        data = await socket.recv(2)
        raw += data

        head1, head2 = struct.unpack("!BB", data)

        fin = True if head1 & 0b10000000 else False
        rsv1 = True if head1 & 0b01000000 else False

        rsv2 = True if head1 & 0b00100000 else False
        rsv3 = True if head1 & 0b00010000 else False

        opcode = WebSocketOpcode(head1 & 0b00001111)
        length = head2 & 0b01111111

        if length == 126:
            data = await socket.recv(2)
            raw += data

            length = struct.unpack("!H", data)[0]

        elif length == 127:
            data = await socket.recv(8)
            raw += data

            length = struct.unpack("!Q", data)[0]

        if socket.is_bound:
            mask_bits = await socket.recv(4)
            raw += data

        data = await socket.recv(length)
        raw += data

        if socket.is_bound:
            data = cls.mask(data, mask_bits)

        frame = cls(
            opcode=opcode,
            fin=fin,
            rsv1=rsv1,
            rsv2=rsv2,
            rsv3=rsv3,
            data=data
        )

        return opcode, raw, frame
"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from typing import Any, Tuple, Dict, Coroutine, Callable, Optional
import struct
import os
import json
import enum

class WebSocketOpcode(enum.IntEnum):
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA

class WebSocketCloseCode(enum.IntEnum):
    NORMAL = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED = 1003
    RESERVED = 1004
    NO_STATUS = 1005
    ABNORMAL = 1006
    UNSUPPORTED_PAYLOAD = 1007
    POLICY_VIOLATION = 1008
    TOO_LARGE = 1009
    MANDATORY_EXTENSION = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    BAD_GATEWAY = 1014
    TLS_HANDSHAKE = 1015

__all__ = (
    'Data',
    'WebSocketFrame',
    'WebSocketCloseCode',
    'WebSocketOpcode',
)

class Data:
    def __init__(self, raw: bytearray, frame: 'WebSocketFrame') -> None:
        self.raw = raw
        self.frame = frame

    @property
    def opcode(self):
        return self.frame.opcode

    @property
    def data(self):
        return self.frame.data

    def encode(self, opcode: Optional[WebSocketOpcode]=None, *, masked: bool=False):
        frame = WebSocketFrame(
            opcode=WebSocketOpcode.TEXT if opcode is None else opcode,
            data=self.data
        )   

        return frame.encode(masked)

    def as_string(self):
        return self.data.decode()

    def as_json(self) -> Dict[str, Any]:
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
    def mask(data: bytes, mask: bytes) -> bytes:
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

    # from https://github.com/aaugustin/websockets/blob/main/src/websockets/legacy/framing.py#L44
    # but with some modifications

    @classmethod
    async def decode(cls, read: Callable[[int], Coroutine[None, None, bytes]], mask: bool=True) -> Tuple[WebSocketOpcode, bytearray, 'WebSocketFrame']:
        raw = bytearray()

        data = await read(2)
        raw += data

        head1, head2 = struct.unpack("!BB", data)

        fin = True if head1 & 0b10000000 else False
        rsv1 = True if head1 & 0b01000000 else False

        rsv2 = True if head1 & 0b00100000 else False
        rsv3 = True if head1 & 0b00010000 else False

        opcode = WebSocketOpcode(head1 & 0b00001111)
        length = head2 & 0b01111111

        if length == 126:
            data = await read(2)
            raw += data

            length = struct.unpack("!H", data)[0]

        elif length == 127:
            data = await read(8)
            raw += data

            length = struct.unpack("!Q", data)[0]

        if mask:
            mask_bits = await read(4)

        raw += data

        data = await read(length)
        raw += data

        if mask:
            data = cls.mask(data, mask_bits) # type: ignore

        frame = cls(
            opcode=opcode,
            fin=fin,
            rsv1=rsv1,
            rsv2=rsv2,
            rsv3=rsv3,
            data=data
        )

        return opcode, raw, frame

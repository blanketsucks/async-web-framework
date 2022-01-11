from __future__ import annotations

from typing import (
    TYPE_CHECKING, 
    Any, 
    Dict, 
    Coroutine,
    Callable, 
    Literal, 
    Optional, 
    Tuple, 
    Type, 
    TypeVar, 
    overload
)
import struct
import os
import json

from railway.types import BytesLike
from .enums import WebSocketCloseCode, WebSocketOpcode, VALID_CLOSE_CODES, VALID_OPCODES
from .errors import (
    InvalidWebSocketCloseCode,
    InvalidWebSocketControlFrame,
    InvalidWebSocketFrame,
    InvalidWebSocketOpcode,
    FragmentedControlFrame
)

if TYPE_CHECKING:
    Reader = Callable[[int], Coroutine[Any, Any, bytes]]
    Format = Literal['short', 'longlong', 'head']

    from enum import IntEnum
    _T = TypeVar('_T', bound=IntEnum)

SHORT = struct.Struct('!H')
LONGLONG = struct.Struct('!Q')
HEAD = struct.Struct('!BB')

FORMATS = {
    'short': SHORT,
    'longlong': LONGLONG,
    'head': HEAD
}


def _try_enum(enum: Type[_T], value: int) -> int:
    try:
        return enum(value)
    except ValueError:
        return value


__all__ = (
    'Data',
    'WebSocketFrame',
)


class Data:
    """
    Returned by :meth:`~railway.websockets.ServerWebSocket.receive`.

    Attributes
    -----------
    frame: :class:`~railway.websockets.frame.WebSocketFrame`
        The frame received.
    """
    def __init__(self, frame: WebSocketFrame) -> None:
        self.frame = frame

    def __repr__(self) -> str:
        return f'<Data frame={self.frame}>'

    @property
    def opcode(self) -> int:
        """
        The opcode of the frame.
        """
        return self.frame.opcode

    @property
    def data(self) -> bytes:
        """
        The data received as bytes.
        """
        return self.frame.data

    def as_string(self):
        """
        The data received as a string.
        """
        return self.data.decode()

    def as_json(self) -> Dict[str, Any]:
        """
        The data received as a JSON object.
        """
        string = self.as_string()
        return json.loads(string)


class WebSocketFrame:
    """
    Represents a websocket data frame.

    Parameters
    -----------
    data: :class:`bytes`
        The frame's data. Can be any bytes-like object.
    head: :class:`int`
        The frame's header.
    """
    def __init__(self, *, data: BytesLike, head: int = 0):
        self.data = bytes(data)

        self._head = head
        self._close_code: Optional[int] = None
        self._opcode: int = None  # type: ignore
    
    def __repr__(self) -> str:
        attrs = ('fin', 'rsv1', 'rsv2', 'rsv3')
        s = ' '.join(f'{name}={getattr(self, name)!r}' for name in attrs)
        return f'<{self.__class__.__name__} {s}>'

    def _get_close_code(self) -> int:
        data = self.data

        if len(self.data) < 2:
            raise InvalidWebSocketFrame('Received a close frame but without a close code')

        code, = SHORT.unpack(data[:2])
        
        if code not in VALID_CLOSE_CODES:
            raise InvalidWebSocketCloseCode(code)

        self.data = data[2:]
        return _try_enum(WebSocketCloseCode, code)

    def _modify_head(self, value: bool, bit: int):
        if value:
            self._head |= value << bit
        else:
            self._head &= ~(1 << bit)

    @classmethod
    def create(cls, data: BytesLike, *, opcode: WebSocketOpcode):
        """
        Creates a non-control frame.

        Parameters
        ----------
        data: :class:`bytes`
            The frame's data. Can be any bytes-like object.
        opcode: :class:`~.WebSocketOpcode`
            The frame's opcode
        """
        self = cls(data=data)

        self.opcode = opcode
        self.fin = True

        return self

    @classmethod
    def create_control_frame(cls, data: BytesLike, *, opcode: WebSocketOpcode):
        """
        Creates a control frame.

        Parameters
        ----------
        data: :class:`bytes`
            The frame's data. Can be any bytes-like object.
        opcode: :class:`~.WebSocketOpcode`
            The frame's opcode
        """
        self = cls.create(data=data, opcode=opcode)
        self.fin = False

        return self

    @classmethod
    async def decode(cls, reader: Reader) -> WebSocketFrame:
        """
        Decodes a websocket frame.

        Parameters
        ----------
        reader: Callable[[int], Coroutine[Any, Any, bytes]]
            A coroutine function that takes in an integer and returns the data read.
            The data read will be and must be of the length passed in.

        Raises
        -------
        InvalidWebSocketOpcode
            If the opcode received is not a valid one.
        InvalidWebSocketFrame
            If the frame received has reserved bits set to 1 or True.
        FragmentedControlFrame
            If the control frame received is fragmented.
        InvalidWebSocketControlFrame
            If the control frame received's data length is more than 125.
        """
        fbyte, sbyte = await cls.unpack(reader, 2, 'head')

        masked = sbyte & 0x80
        length = sbyte & 0x7F

        mask = None

        if length == 126:
            length, = await cls.unpack(reader, 2, 'short')
        elif length == 127:
            length, = await cls.unpack(reader, 8, 'longlong')

        if masked:
            mask = await reader(4)

        data = await reader(length)

        if masked:
            assert mask is not None, 'Should never happen'
            data = cls.mask(data, mask)

        opcode = fbyte & 0x0F
        if opcode not in VALID_OPCODES:
            raise InvalidWebSocketOpcode(opcode)

        frame = cls(head=fbyte, data=data)
        if any((frame.rsv1, frame.rsv2, frame.rsv3)):
            raise InvalidWebSocketFrame('Received a frame with reserved bits set')

        if frame.opcode is WebSocketOpcode.CLOSE:
            frame.close_code = frame._get_close_code()

        if frame.is_control():
            if frame.fin:
                raise FragmentedControlFrame

            if len(frame.data) > 125:
                raise InvalidWebSocketControlFrame(
                    'Received a control frame with a payload length of more than 125 bytes'
                )

        return frame

    @overload
    @staticmethod
    async def unpack(reader: Reader, size: int, format: Literal['short', 'longlong']) -> Tuple[int]:
        ...
    @overload
    @staticmethod
    async def unpack(reader: Reader, size: int, format: Literal['head']) -> Tuple[int, int]:
        ...
    @staticmethod
    async def unpack(reader: Reader, size: int, format: Format) -> Tuple[int, ...]:
        """
        Reads data from the reader and unpacks the data.
        Valid formats are: ``short``, ``longlong``, ``head``.

        Parameters
        ----------
        reader: Callable[[int], Coroutine[Any, Any, bytes]]
            A coroutine function that takes in an integer and returns the data read.
            The data read will be and must be of the length passed in.
        size: :class:`int`
            The size of the data to be read.
        format: :class:`str`
            The format to unpack the data with.

        Raises
        -------
        ValueError
            If the format is not valid.
        """
        data = await reader(size)
        struct = FORMATS.get(format)
        if not struct:
            raise ValueError(f'Unknown format {format}')

        return struct.unpack(data)

    @staticmethod
    def pack(data: int, format: Format) -> bytes:
        """
        Packs the data into the format.
        Valid formats are: ``short``, ``longlong``, ``head``.

        Parameters
        ----------
        data: :class:`int`
            The data to be packed.
        format: :class:`str`
            The format to pack the data with.
        
        Raises
        -------
        ValueError
            If the format is not valid.
        """
        fmt = FORMATS.get(format)
        if not fmt:
            raise ValueError(f'Unknown format {format}')

        return fmt.pack(data)

    @staticmethod
    def mask(data: bytes, mask: bytes) -> bytes:
        """
        Masks the data passed in.

        Parameters
        ----------
        data: :class:`bytes`
            The data to mask.
        mask: :class:`bytes`
            The mask to use.
        """
        return bytes([data[i] ^ mask[i % 4] for i in range(len(data))])

    @property
    def opcode(self) -> int:
        """
        The frame's opcode
        """
        return _try_enum(WebSocketOpcode, self._head & 0x0F)

    @opcode.setter
    def opcode(self, value: WebSocketOpcode):
        self._head |= int(value)

    @property
    def fin(self) -> bool:
        """
        Whether the frame is the final frame in a fragmented message.
        """
        return bool(self._head & 0x80)

    @fin.setter
    def fin(self, value: bool):
        self._modify_head(value, 7)

    @property
    def rsv1(self) -> bool:
        return bool(self._head & 0x40)

    @rsv1.setter
    def rsv1(self, value: bool):
        self._modify_head(value, 6)

    @property
    def rsv2(self) -> bool:
        return bool(self._head & 0x20)

    @rsv2.setter
    def rsv2(self, value: bool):
        self._modify_head(value, 5)

    @property
    def rsv3(self) -> bool:
        return bool(self._head & 0x10)

    @rsv3.setter
    def rsv3(self, value: bool):
        self._modify_head(value, 4)

    @property
    def close_code(self) -> Optional[int]:
        return self._close_code

    @close_code.setter
    def close_code(self, value: int):
        self._close_code = value

    def is_control(self) -> bool:
        """
        Whether this frame is a control frame or not
        """
        return self.opcode > 0x7

    def ensure(self) -> None:
        """
        Ensures all the frame's values are valid.

        Raises
        -------
        InvalidWebSocketFrame
            If the frame's reserve bits are set to 1 or True, or when the frame has a close code set
            but the opcode isn't :attr:`.WebSocketOpCode.CLOSE`.
        InvalidWebSocketControlFrame
            If the control frame's data exceeds the 125 bytes in length
        FragmentedControlFrame
            If the control frame is fragmented
        """
        if any((self.rsv1, self.rsv2, self.rsv3)):
            raise InvalidWebSocketFrame('Frame reserve bits must be set to False or 0')

        if self.close_code:
            if self.opcode is not WebSocketOpcode.CLOSE:
                raise InvalidWebSocketFrame(
                    'Close code set but opcode is not WebSocketOpcode.CLOSE'
                )
        elif self.opcode is WebSocketOpcode.CLOSE and self.close_code is None:
            raise InvalidWebSocketFrame(
                'opcode set to WebSocketOpcode.CLOSE but no close code was set'
            )

        if self.is_control():
            length = len(self.data)

            if length > 125:
                raise InvalidWebSocketControlFrame('Control frames must not exceed 125 bytes in length')

            if self.fin:
                raise FragmentedControlFrame(False)

    def encode(self, masked: bool = False) -> bytearray:
        """
        Encodes the frame into a sendable buffer.

        Parameters
        ----------
        masked: :class:`bool`
            Whether to mask the data or not.
        """
        self.ensure()
        data = self.data

        if self.close_code is not None:
            data = self.pack(self.close_code, 'short') + data

        buffer = bytearray(2)
        length = len(data)

        buffer[0] = self._head
        buffer[1] = masked << 7

        if length < 126:
            buffer[1] |= length
        elif length < 0xFFFF:
            buffer[1] |= 126

            packed = self.pack(length, 'short')
            buffer.extend(packed)
        else:
            buffer[1] |= 127

            packed = self.pack(length, 'longlong')
            buffer.extend(packed)

        if masked:
            mask = os.urandom(4)

            buffer.extend(mask)
            data = self.mask(data, mask)

        buffer.extend(data)
        return buffer


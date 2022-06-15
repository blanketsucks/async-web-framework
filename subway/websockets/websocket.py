from typing import Any, Dict, List, Optional, Union
import asyncio

from subway.streams import StreamProtocol, StreamReader, StreamWriter, get_address
from subway.utils import clear_docstring, warn, dumps
from subway.types import BytesLike
from .frame import WebSocketFrame, WebSocketOpcode, Data, WebSocketCloseCode
from .enums import WebSocketState
from .errors import WebSocketError, WebSocketWarning

__all__ = (
    'WebSocketProtocol',
    'ServerWebSocket',
    'ClientWebSocket',
    'WebSocket'
)

WebSocketData = Union[str, BytesLike, Dict[Any, Any], List[Any]]

class WebSocketProtocol(StreamProtocol):
    def __init__(self, reader: StreamReader, writer: StreamWriter, waiter: asyncio.Future[None]) -> None:
        self.reader = reader
        self.writer = writer
        self.waiter = waiter

    async def wait_until_connected(self) -> None:
        await asyncio.sleep(0)


class BaseWebSocket:
    """
    A base websocket class.
    Subclasses of this class override the :meth:`send_frame` to either mask or not mask the frame.

    Parameters
    -----------
    writer: :class:`~subway.streams.StreamWriter`
        The writer to use.
    reader: :class:`~subway.streams.StreamReader`
        The reader to use.
    """
    def __init__(self, writer: StreamWriter, reader: StreamReader) -> None:
        self._writer = writer
        self._reader = reader
        self._closed = False
        self._received_close_frame = False
        self._state = WebSocketState.OPEN

    def __repr__(self) -> str:
        return f'<WebSocket state={self.state}>'

    def __aiter__(self):
        return self

    async def __anext__(self) -> Data:
        data = await self.receive()
        if data.opcode is WebSocketOpcode.CLOSE:
            raise StopAsyncIteration

        return data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
        await self.wait_closed()

    def _set_state(self, state: WebSocketState):
        self._state = state

    @property
    def state(self):
        """
        The state of the websocket.
        """
        return self._state

    @property
    def writer(self):
        """
        The writer to use.
        """
        return self._writer

    @property
    def reader(self):
        """
        The reader to use.
        """
        return self._reader

    @property
    def sockname(self):
        """
        The address of the local endpoint.
        """
        return get_address(self.writer, 'sockname')

    @property
    def peername(self):
        """
        The address of the remote endpoint.
        """
        return get_address(self.writer, 'peername')

    def create_frame(self, data: WebSocketData, opcode: WebSocketOpcode, *, control: bool = False) -> WebSocketFrame:
        """
        Creates a frame.

        Parameters
        -----------
        data: Any
            The data to send.
        opcode: :class:`~subway.websockets.frame.WebSocketOpcode`
            The opcode to use.
        control: :class:`bool`
            Whether the frame is a control frame.
        """
        if isinstance(data, (list, dict)):
            data = dumps(data)
        if isinstance(data, str):
            data = data.encode()

        if control:
            return WebSocketFrame.create_control_frame(data, opcode=opcode)

        return WebSocketFrame.create(data, opcode=opcode)

    def is_closed(self):
        """
        True if the websocket has been closed.
        """
        return self._closed or self._state is WebSocketState.CLOSED

    def should_close(self) -> bool:
        """
        True if the websocket should be closed.
        """
        return self._state is WebSocketState.CLOSING or self._received_close_frame

    async def wait_closed(self) -> None:
        """
        Waits until the websocket is closed.
        """
        await self.writer.wait_closed()

    async def send_frame(self, frame: WebSocketFrame, *, masked: bool = True) -> int:
        """
        Sends a frame.

        Parameters
        -----------
        frame: :class:`~subway.websockets.frame.WebSocketFrame`
            The frame to send.
        """
        if self.is_closed():
            raise WebSocketError('websocket is closed')

        if self.should_close() and frame.opcode is not WebSocketOpcode.CLOSE:
            warn('websocket is closing, sending frame anyway.', WebSocketWarning, stacklevel=5)

        data = frame.encode(masked=masked)
        self._set_state(WebSocketState.SENDING)

        await self.writer.write(data, drain=True)
        self._set_state(WebSocketState.OPEN)

        return len(data)

    async def send_bytes(self, data: BytesLike, *, opcode: Optional[WebSocketOpcode]=None):
        """
        Sends bytes.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send. Can be any bytes-like object.
        opcode: :class:`~subway.websockets.frame.WebSocketOpcode`
            The opcode to use. Defaults to :attr:`~subway.websockets.frame.WebSocketOpcode.TEXT`.
        """
        if opcode is None:
            opcode = WebSocketOpcode.TEXT

        frame = self.create_frame(data, opcode=opcode)
        return await self.send_frame(frame)

    async def send(self, data: BytesLike, *, opcode: Optional[WebSocketOpcode]=None):
        """
        An alias for :meth:`~subway.websockets.websocket.ServerWebSocket.send_bytes`.
        """
        return await self.send_bytes(data, opcode=opcode)

    async def send_str(self, data: str, *, opcode: Optional[WebSocketOpcode]=None):
        """
        Sends a string.

        Parameters
        -----------
        data: :class:`str`
            The data to send.
        opcode: :class:`~subway.websockets.frame.WebSocketOpcode`
            The opcode to use. Defaults to :attr:`~subway.websockets.frame.WebSocketOpcode.TEXT`.
        """
        return await self.send_bytes(data.encode(), opcode=opcode)

    async def send_json(self, data: Union[List[Any], Dict[str, Any]], *, opcode: Optional[WebSocketOpcode]=None):
        """
        Sends a JSON object.

        Parameters
        -----------
        data: :class:`dict`
            The data to send.
        opcode: :class:`~subway.websockets.frame.WebSocketOpcode`
            The opcode to use. Defaults to :attr:`~subway.websockets.frame.WebSocketOpcode.TEXT`.
        """
        return await self.send_str(dumps(data), opcode=opcode)

    async def continuation(self, data: BytesLike):
        """
        Sends ``data`` with the :attr:`~subway.websockets.frame.WebSocketOpcode.CONTINUATION` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send. Can be any bytes-like object.
        """
        return await self.send_bytes(data, opcode=WebSocketOpcode.CONTINUATION)

    async def binary(self, data: BytesLike):
        """
        Sends ``data`` with the :attr:`~subway.websockets.frame.WebSocketOpcode.BINARY` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send. Can be any bytes-like object.
        """
        return await self.send_bytes(data, opcode=WebSocketOpcode.BINARY)

    async def ping(self, data: BytesLike):
        """
        Sends ``data`` with the :attr:`~subway.websockets.frame.WebSocketOpcode.PING` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send. Can be any bytes-like object.
        """
        frame = self.create_frame(data, opcode=WebSocketOpcode.PING, control=True)
        return await self.send_frame(frame)

    async def pong(self, data: BytesLike):
        """
        Sends ``data`` with the :attr:`~subway.websockets.frame.WebSocketOpcode.PONG` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send. Can be any bytes-like object.
        """
        frame = self.create_frame(data, opcode=WebSocketOpcode.PONG, control=True)
        return await self.send_frame(frame)

    async def close(self, data: Optional[BytesLike] = None, *, code: Optional[WebSocketCloseCode]=None) -> None:
        """
        Closes the websocket.
        Sends ``data`` with the :attr:`~subway.websockets.frame.WebSocketOpcode.Close` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send. Can be any bytes-like object.
        code: :class:`~subway.websockets.frame.WebSocketCloseCode`
            The close code to send. Defaults to :attr:`~subway.websockets.frame.WebSocketCloseCode.NORMAL`.
        """
        if not code:
            code = WebSocketCloseCode.NORMAL

        if not data:
            data = b''

        frame = self.create_frame(data, opcode=WebSocketOpcode.CLOSE, control=True)
        frame.close_code = code.value

        await self.send_frame(frame) 
        self.writer.close()

        self._set_state(WebSocketState.CLOSED)
        self._closed = True  

    async def receive(self) -> Data:
        """
        Receives data.
        """
        if self.is_closed():
            raise WebSocketError('websocket is closed')

        if self.should_close():
            msg = 'websocket is closing, receiving frame anyway. This might block the current task forever.'
            warn(msg, WebSocketWarning, stacklevel=5)

        self._set_state(WebSocketState.RECEIVING)
        frame = await WebSocketFrame.decode(self.reader.read)

        self._set_state(WebSocketState.OPEN)
        data = Data(frame)

        if data.opcode is WebSocketOpcode.CLOSE:
            self._received_close_frame = True
            self._set_state(WebSocketState.CLOSING)

        return data

    async def receive_bytes(self):
        """
        Receives bytes.
        """
        data = await self.receive()
        return data.data

    async def receive_str(self):
        """
        Receives a string.
        """
        data = await self.receive()
        return data.text()

    async def receive_json(self):
        """
        Receives a JSON object.
        """
        data = await self.receive()
        return data.json()


class ServerWebSocket(BaseWebSocket):
    """
    A server-side websocket.
    """
    @clear_docstring
    def send_frame(self, frame: WebSocketFrame):
        return super().send_frame(frame, masked=False)

class ClientWebSocket(BaseWebSocket):
    """
    A client-side websocket.
    The only difference from the other class is that the frame sent is masked.
    """
    @clear_docstring
    def send_frame(self, frame: WebSocketFrame):
        return super().send_frame(frame, masked=True)


WebSocket = ServerWebSocket
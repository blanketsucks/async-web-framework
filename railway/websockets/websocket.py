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
from typing import Any, Dict, Tuple, Optional
import json

from .frame import WebsocketFrame, WebsocketOpcode, Data, WebsocketCloseCode
from .enums import WebsocketState
from .errors import WebsocketError, WebsocketWarning
from railway.streams import StreamTransport
from railway.utils import clear_docstring, warn

__all__ = (
    'ServerWebsocket',
    'ClientWebsocket',
)

class ServerWebsocket:
    """
    A server-side websocket.

    Parameters
    -----------
    transport: :class:`~railway.streams.StreamTransport`
        The transport used by the websocket.
    """
    def __init__(self, transport: StreamTransport) -> None:
        self._transport = transport

        self._closed = False
        self._state = WebsocketState.OPEN

    def __repr__(self) -> str:
        return f'<Websocket peername={self.peername}>'

    def _set_state(self, state: WebsocketState):
        self._state = state

    @property
    def state(self):
        """
        The state of the websocket.
        """
        return self._state

    @property
    def peername(self) -> Tuple[str, int]:
        """
        The peername of the websocket.
        """
        return self._transport.get_extra_info('peername')

    def is_closed(self):
        """
        True if the websocket has been closed.
        """
        return self._closed or self._state is WebsocketState.CLOSED

    def should_close(self) -> bool:
        """
        True if the websocket should be closed.
        """
        return self._state is WebsocketState.CLOSING

    def feed_data(self, data: bytes):
        """
        Feeds data into the websocket's internal reader.
        """
        return self._transport.feed_data(data)

    async def send_frame(self, frame: WebsocketFrame) -> int:
        """
        Sends a frame.

        Parameters
        -----------
        frame: :class:`~railway.websockets.frame.WebsocketFrame`
            The frame to send.
        """
        if self.is_closed():
            raise WebsocketError('websocket is closed')

        if self.should_close() and frame.opcode is not WebsocketOpcode.CLOSE:
            warn('websocket is closing, sending frame anyway.', WebsocketWarning, stacklevel=5)

        data = frame.encode()
        self._set_state(WebsocketState.SENDING)

        await self._transport.write(data)
        self._set_state(WebsocketState.OPEN)

        return len(data)

    async def send_bytes(self, data: bytes, *, opcode: Optional[WebsocketOpcode]=None):
        """
        Sends bytes.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send.
        opcode: :class:`~railway.websockets.frame.WebsocketOpcode`
            The opcode to use. Defaults to :attr:`~railway.websockets.frame.WebsocketOpcode.TEXT`.
        """
        if opcode is None:
            opcode = WebsocketOpcode.TEXT

        frame = WebsocketFrame.create(data, opcode=opcode)
        return await self.send_frame(frame)

    async def send(self, data: bytes, *, opcode: Optional[WebsocketOpcode]=None):
        """
        An alias for :meth:`~railway.websockets.websocket.ServerWebsocket.send_bytes`.
        """
        return await self.send_bytes(data, opcode=opcode)

    async def send_str(self, data: str, *, opcode: Optional[WebsocketOpcode]=None):
        """
        Sends a string.

        Parameters
        -----------
        data: :class:`str`
            The data to send.
        opcode: :class:`~railway.websockets.frame.WebsocketOpcode`
            The opcode to use. Defaults to :attr:`~railway.websockets.frame.WebsocketOpcode.TEXT`.
        """
        return await self.send_bytes(data.encode(), opcode=opcode)

    async def send_json(self, data: Dict[str, Any], *, opcode: Optional[WebsocketOpcode]=None):
        """
        Sends a JSON object.

        Parameters
        -----------
        data: :class:`dict`
            The data to send.
        opcode: :class:`~railway.websockets.frame.WebsocketOpcode`
            The opcode to use. Defaults to :attr:`~railway.websockets.frame.WebsocketOpcode.TEXT`.
        """
        return await self.send_str(json.dumps(data), opcode=opcode)

    async def continuation(self, data: bytes):
        """
        Sends ``data`` with the :attr:`~railway.websockets.frame.WebsocketOpcode.CONTINUATION` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send.
        """
        return await self.send_bytes(data, opcode=WebsocketOpcode.CONTINUATION)

    async def binary(self, data: bytes):
        """
        Sends ``data`` with the :attr:`~railway.websockets.frame.WebsocketOpcode.BINARY` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send.
        """
        return await self.send_bytes(data, opcode=WebsocketOpcode.BINARY)

    async def ping(self, data: bytes):
        """
        Sends ``data`` with the :attr:`~railway.websockets.frame.WebsocketOpcode.PING` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send.
        """
        frame = WebsocketFrame.create_control_frame(
            data=data,
            opcode=WebsocketOpcode.PING,
        )

        return await self.send_frame(frame)

    async def pong(self, data: bytes):
        """
        Sends ``data`` with the :attr:`~railway.websockets.frame.WebsocketOpcode.PONG` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send.
        """
        frame = WebsocketFrame.create_control_frame(
            data=data,
            opcode=WebsocketOpcode.PONG,
        )

        return await self.send_frame(frame)

    async def close(self, data: bytes, *, code: Optional[WebsocketCloseCode]=None) -> None:
        """
        Closes the websocket.
        Sends ``data`` with the :attr:`~railway.websockets.frame.WebsocketOpcode.Close` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send.
        code: :class:`~railway.websockets.frame.WebsocketCloseCode`
            The close code to send. Defaults to :attr:`~railway.websockets.frame.WebsocketCloseCode.NORMAL`.
        """
        if not code:
            code = WebsocketCloseCode.NORMAL

        frame = WebsocketFrame.create_control_frame(
            data=data,
            opcode=WebsocketOpcode.CLOSE,
        )
        frame.close_code = code.value

        await self.send_frame(frame) 
        self._transport.close()

        self._set_state(WebsocketState.CLOSED)
        self._closed = True  

    async def wait_closed(self) -> None:
        """
        Waits until the websocket is fully closed.
        """
        await self._transport.wait_closed()

    async def receive(self) -> Data:
        """
        Receives data.
        """
        if self.is_closed():
            raise WebsocketError('websocket is closed')

        if self.should_close():
            warn('websocket is closing, receiving frame anyway.', WebsocketWarning, stacklevel=5)

        self._set_state(WebsocketState.RECEIVING)
        frame = await WebsocketFrame.decode(self._transport.receive)

        self._set_state(WebsocketState.OPEN)
        data = Data(frame)

        if data.opcode is WebsocketOpcode.CLOSE:
            self._set_state(WebsocketState.CLOSING)

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
        return data.as_string()

    async def receive_json(self):
        """
        Receives a JSON object.
        """
        data = await self.receive()
        return data.as_json()

class ClientWebsocket(ServerWebsocket):
    """
    A client-side websocket.
    The only difference from the other class is that the frame sent is masked.
    """

    @clear_docstring
    async def send_frame(self, frame: WebsocketFrame):
        data = frame.encode(masked=True)
        await self._transport.write(data)

        return len(data)

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
from railway.streams import StreamTransport

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

        self.peername: Tuple[str, int] = transport.get_extra_info('peername')
        self._closed = False

    def __repr__(self) -> str:
        return f'<Websocket peername={self.peername}>'

    def is_closed(self):
        """
        True if the websocket has been closed.
        """
        return self._closed

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
        data = frame.encode()
        await self._transport.write(data)

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
        if not opcode:
            opcode = WebsocketOpcode.TEXT

        frame = WebsocketFrame(opcode=opcode, data=data)
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

    async def ping(self, data: bytes):
        """
        Sends ``data`` with the :attr:`~railway.websockets.frame.WebsocketOpcode.PING` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send.
        """
        await self.send_bytes(data, opcode=WebsocketOpcode.PING)

    async def pong(self, data: bytes):
        """
        Sends ``data`` with the :attr:`~railway.websockets.frame.WebsocketOpcode.PONG` opcode.

        Parameters
        -----------
        data: :class:`bytes`
            The data to send.
        """
        return await self.send_bytes(data, opcode=WebsocketOpcode.PONG)

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

    async def close(self, data: bytes, code: Optional[WebsocketCloseCode]=None) -> None:
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

        close = code.to_bytes(2, 'big', signed=False) # type: ignore
        frame = WebsocketFrame(opcode=WebsocketOpcode.CLOSE, data=close + data)

        self._closed = True
        await self.send_frame(frame)

        self._transport.close()     

    async def receive(self) -> Data:
        """
        Receives data.
        """
        opcode, raw, data = await WebsocketFrame.decode(self._transport.receive)
        return Data(raw, data)

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
    """

    async def send_frame(self, frame: WebsocketFrame):
        data = frame.encode(masked=True)
        await self._transport.write(data)

        return len(data)

    async def receive(self):
        opcode, raw, data = await WebsocketFrame.decode(self._transport.receive, masked=False)
        return Data(raw, data)

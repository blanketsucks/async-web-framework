from typing import TYPE_CHECKING, Any, Optional
import os
import base64

from railway.streams import open_connection
from railway.url import URL
from railway.types import StrURL
from railway.response import HTTPStatus
from railway.websockets import ClientWebSocket as WebSocket, WebSocketCloseCode
from .request import HTTPRequest
from .abc import Hooker
from .errors import HandshakeError
from .response import HTTPResponse

if TYPE_CHECKING:
    from .sessions import HTTPSession

__all__ = (
    'WebSocket',
    'TCPHooker',
    'WebSocketHooker'
)

class TCPHooker(Hooker):
    def __init__(self, session: 'HTTPSession') -> None:
        super().__init__(session)

    async def connect(self, url: StrURL) -> Any:
        self.ensure()

        if isinstance(url, str):
            url = URL(url)

        port = url.default_port
        host = url.hostname
        ssl_context = self.create_default_ssl_context() if port == 443 else None

        reader, writer = await open_connection(
            host=host,
            port=port,
            ssl=ssl_context
        )

        self.connected = True
        self.reader = reader
        self.writer = writer

    async def write(self, data: HTTPRequest) -> None:
        if not self.writer:
            raise RuntimeError('Not connected')

        await self.writer.write(data.prepare(), drain=True)

    async def close(self) -> None:
        if not self.writer:
            return

        self.writer.close()
        await self.writer.wait_closed()

        self.connected = False
        self.closed = True

class WebSocketHooker(TCPHooker):
    def __init__(self, session: 'HTTPSession') -> None:
        super().__init__(session)

        self._task = None

    async def connect(self, url: StrURL) -> WebSocket:
        await super().connect(url)
        ws = await self.handshake(url.path, url.hostname) # type: ignore

        return ws

    def generate_websocket_key(self) -> bytes:
        return base64.b64encode(os.urandom(16))

    def create_websocket(self) -> WebSocket:
        if self.writer is None or self.reader is None:
            raise RuntimeError('Not connected')

        return WebSocket(self.reader, self.writer) # type: ignore
    
    async def handshake(self, path: str, host: str) -> WebSocket:
        if not self.writer:
            raise HandshakeError('Not connected', hooker=self)

        key = self.generate_websocket_key().decode()
        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': key,
            'Sec-WebSocket-Version': 13
        }

        request = self.build_request('GET', host, path, headers, None)
        await self.write(request)

        response = await self.get_response()

        self.websocket = self.create_websocket()
        await self.verify_handshake(response)

        return self.websocket

    async def verify_handshake(self, response: HTTPResponse) -> None:
        headers = response.headers

        if response.status is not HTTPStatus.SWITCHING_PROTOCOLS:
            return await self._close(
                HandshakeError(
                    message=f"Expected status code 101, but received {response.status.value!r} instead",
                    hooker=self
                )
            )

        connection = headers.get('Connection')
        if connection is None or connection.lower() != 'upgrade':
            return await self._close(
                HandshakeError(
                    message=f"Expected 'Connection' header with value 'upgrade', but got {connection!r} instead",
                    hooker=self,
                )
            )

        upgrade = response.headers.get('Upgrade')
        if upgrade is None or upgrade.lower() != 'websocket':
            return await self._close(
                HandshakeError(
                    message=f"Expected 'Upgrade' header with value 'websocket', but got {upgrade!r} instead",
                    hooker=self,
                )
            )

    async def _close(self, exc: Exception) -> None:
        await self.close()
        raise exc

    async def close(self, *, data: Optional[bytes]=None, code: Optional[WebSocketCloseCode]=None) -> None:
        if not self.websocket or self.websocket.is_closed():
            return

        await self.websocket.close(data, code=code)
        await self.websocket.wait_closed()

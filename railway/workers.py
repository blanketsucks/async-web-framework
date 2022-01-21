from __future__ import annotations

from typing import TYPE_CHECKING, Any
import asyncio
import logging
import datetime

from .utils import CLRF
from .server import TCPServer
from .request import Request
from .streams import StreamWriter, StreamReader
from .errors import PartialRead
from .responses import HTTPVersionNotSupported
from . import websockets

if TYPE_CHECKING:
    from .app import Application

__all__ = 'Worker',

log = logging.getLogger(__name__)
    
class Worker(TCPServer):
    """
    A worker class used by the application to handle requests.
    This class is responsible for handling requests from clients and forwarding them to the application. 
    It also handles incoming websocket requests.

    Parameters
    ----------
    app: :class:`~railway.app.Application`
        The application instance.
    id: :class:`int`
        The id of the worker.

    Attributes
    ----------
    app: :class:`railway.app.Application`
        The application instance.
    id: :class:`int`
        The id of the worker.
    """

    def __init__(self, app: Application, id: int):
        self.app: Application = app
        self.id: int = id

        self._ready = asyncio.Event()
        self._serving = False

        super().__init__(loop=app.loop, ssl_context=app.ssl_context)

    def __repr__(self) -> str:
        return '<Worker id={0.id}>'.format(self)

    def is_serving(self) -> bool:
        """
        True if the worker is currently serving requests.
        """
        return self._serving

    async def wait_until_ready(self):
        """
        Waits until the worker is fully ready to serve requests.
        """
        await self._ready.wait()

    async def serve(self, *args: Any, **kwargs: Any) -> None: 
        await super().serve(sock=self.app.socket)

        self._ready.set()
        self._serving = True

    async def close(self):
        """
        closes the worker.
        """
        await super().close()
        
        self._ready.clear()
        self.app.dispatch('worker_shutdown', self)
        log.info(f'[Worker-{self.id}] Stopped serving.')

        self._serving = False

    async def on_transport_connect(self, reader: StreamReader, writer: StreamWriter) -> None:
        """
        This function gets called whenever a new connection gets made.
        """
        try:
            status_line = await reader.readuntil(CLRF, timeout=1)
        except (asyncio.TimeoutError, KeyboardInterrupt, PartialRead):
            return writer.close()

        peername = writer.get_extra_info('peername')
        created_at = datetime.datetime.utcnow()

        request = await Request.parse(status_line, reader, writer, self, created_at)
        
        if request.version != 'HTTP/1.1':
            response = HTTPVersionNotSupported()
            return await request.send(response, convert=False)

        self.app.dispatch('request', request, self)
        log.info(f'[Worker-{self.id}] Received a {request.method!r} request to {request.url.path!r} from {peername}')

        websocket = None

        if request.is_websocket():
            websocket = websockets.create_websocket(writer, reader, client_side=False)
            await request.handshake()

        await self.app._request_handler(request=request, websocket=websocket)
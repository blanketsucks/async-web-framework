
import typing
import asyncio
from atom import sockets
import warnings

from atom.datastructures import URL
from . import Request, Response
from .errors import InvalidURL

__all__ = (
    'request',
    'Session'
)

class SessionContextManager:
    def __init__(self, coro: typing.Coroutine[None, None, Response], close: typing.Callable[..., typing.Coroutine]) -> None:
        self._coro = coro
        self._close = close

    async def __aenter__(self):
        return await self._coro

    async def __aexit__(self, *args):
        await self._close()
        return self

    def __await__(self):
        return self.__aenter__().__await__()

class WebsocketContextManager:
    def __init__(self, 
                coro: typing.Coroutine[typing.Any, typing.Any, sockets.WebsocketConnection], 
                close: typing.Callable[..., typing.Coroutine]) -> None:
        
        self._coro = coro
        self._close = close

    async def __aenter__(self):
        return await self._coro

    async def __aexit__(self, *args):
        await self._close()
        return self

    def __await__(self):
        return self.__aenter__().__await__()


class Session:
    def __init__(self, *, loop: asyncio.AbstractEventLoop=...) -> None:
        
        self._loop = sockets.check_ellipsis(loop, asyncio.get_event_loop())
        self._open_socket: typing.Union[sockets.socket, sockets.Websocket] = None

    def __del__(self):
        if self._open_socket is not None:
            warnings.warn(
                message=f'Unclosed session {self!r}',
                category=ResourceWarning,
                source=self
            )

    def _check_socket(self):
        if self._open_socket is not None:
            raise RuntimeError('A connection is already established. Close it before opening a new one')

    def _create_socket(self):
        self._check_socket()
        return sockets.socket(
            loop=self._loop
        )

    def _create_websocket(self):
        self._check_socket()
        return sockets.Websocket(
            loop=self._loop
        )

    def _prepare_request(self, path, method, hdrs):
        return Request(
            method=method,
            path=path,
            version='1.1',
            headers=hdrs
        )

    async def _request(self, 
                    url: typing.Union[str, URL], 
                    method: str=..., 
                    *, 
                    headers: typing.Mapping[str, typing.Any]=...):

        method = 'GET' if method is ... else method
        headers = {} if headers is ... else headers

        if isinstance(url, str):
            url = URL(url)

        ssl = url.scheme == 'https'
        socket = self._create_socket()

        port = 443 if ssl else 80

        await socket.connect(url.hostname, port, ssl=ssl)
        req = self._prepare_request(url.path, method, headers)

        await socket.send(req.encode())
        data = await socket.recvall(32768)

        resp = Response.parse(bytes(data))

        if 'Location' in resp.headers:
            url = resp.headers['Location']
            print(url)
            return await self._request(url, method, headers=headers)

        self._open_socket = socket
        return resp

    async def _connect(self, 
                    url: typing.Union[str, URL], 
                    *, 
                    headers: typing.Mapping[str, typing.Any]=...):
        if headers is ...:
            headers = {}

        if isinstance(url, str):
            url = URL(url)

        if not url.scheme.startswith('ws'):
            raise InvalidURL(url._url)

        ssl = url.scheme == 'wss'
        socket = self._create_websocket()

        port = 443 if ssl else 80
        await socket.connect(url.hostname, url.path, port)

        self._open_socket = socket
        return sockets.WebsocketConnection(socket)

    async def close(self):
        if self._open_socket is None:
            return

        res = self._open_socket.close()

        if asyncio.iscoroutine(res):
            await res

    def request(self, url: typing.Union[str, URL], method: str=..., **kwargs):
        return SessionContextManager(self._request(url, method, **kwargs), self.close)

    def ws_connect(self, url: typing.Union[str, URL], **kwargs):
        return WebsocketContextManager(self._connect(url, **kwargs), self.close)

    
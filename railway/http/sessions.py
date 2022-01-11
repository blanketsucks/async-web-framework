from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
import asyncio
import json as _json

from .hooker import TCPHooker, WebSocketHooker, WebSocket
from .response import HTTPResponse
from .utils import RequestContextManager, WebSocketContextManager
from railway import compat, utils
from railway.types import StrURL

if TYPE_CHECKING:
    from railway import URL

__all__ = (
    'HTTPSession',
    'request',
    'ws_connect',
)

class HTTPSession:
    """
    A class representing an HTTP session.

    Parameters
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop to use.

    Attributes
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used by the session.

    Example
    -------
    .. code-block:: python3

        from railway import http
        import asyncio

        async def request():
            async with http.HTTPSession() as session:
                async with session.request('GET', 'https://example.com/') as response:
                    text = response.text()
                    print(text)

                    headers = response.headers
                    print(headers)

        session.loop.run_until_complete(request())

    """
    def __init__(
        self,
        *,
        headers: Optional[Dict[str, Any]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        self.loop = loop or compat.get_event_loop()
        self.headers = headers or {}

        self._hookers: List[TCPHooker] = []

    def _ensure_hookers(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc: Any):
        await self.close()
        return self

    async def close(self):
        """
        Closes the session.
        """
        for hooker in self._hookers:
            if not hooker.closed:
                await hooker.close()

    def request(
        self,
        url: StrURL,
        method: str,
        *,
        headers: Optional[Dict[str, Any]] = None,
        body: Any = None,
        json: Optional[Dict[str, Any]] = None,
        ignore_redirects: bool = False,
        hooker: Optional[TCPHooker] = None
    ):
        """
        Sends an HTTP request with the given method.

        Parameters
        ----------
        method: :class:`str`
            The HTTP method to use.
        url: :class:`str`
            The URL to request.
        **kwargs: Any
            The keyword arguments to pass to the request.

        Example
        -------
        .. code-block:: python3

            async with session.request('https://example.com/', 'GET') as response:
                text = await response.text()
                print(text)

            # or you could use it without a context manager, but make sure to close the response yourself

            response = await session.request('https://example.com/')
            text = await response.text()
            print(text)

            await response.close()

        """
        coro = self._request(
            url=url, 
            method=method, 
            headers=headers, 
            body=body, 
            json=json, 
            hooker=hooker, 
            ignore_redirects=ignore_redirects
        )
        return RequestContextManager(coro)

    def ws_connect(self, url: Union[str, URL], **kwargs: Any) -> WebSocketContextManager:
        """
        Connects to a URL using websockets.

        Parameters
        ----------
        url: :class:`str`
            The URL to connect to.
        **kwargs: Any
            The keyword arguments to pass to the websocket request.

        Example
        -------
        .. code-block:: python3

            async with session.ws_connect('ws://echo.websocket.org') as ws:
                await ws.send(b'Hello, world!')

                data = await ws.receive()
                print(data.data)

            # or, once again, without a context manager

            ws = await session.ws_connect('ws://echo.websocket.org')
            await ws.send(b'Hello, world!')

            data = await ws.receive()
            print(data.data)
        
        """
        return WebSocketContextManager(self._connect(url))

    def get(self, url: StrURL, **kwargs: Any):
        return self.request(url, 'GET', **kwargs)

    def post(self, url: StrURL, **kwargs: Any):
        return self.request(url, 'POST', **kwargs)

    def put(self, url: StrURL, **kwargs: Any):
        return self.request(url, 'PUT', **kwargs)

    def delete(self, url: StrURL, **kwargs: Any):
        return self.request(url, 'DELETE', **kwargs)

    def head(self, url: StrURL, **kwargs: Any) :
        return self.request(url, 'HEAD', **kwargs)

    async def _request(
        self,
        url: StrURL,
        method: str,
        *,
        headers: Optional[Dict[str, Any]] = None,
        body: Any = None,
        json: Optional[Dict[str, Any]] = None,
        ignore_redirects: bool = False,
        hooker: Optional[TCPHooker] = None
    ) -> HTTPResponse:
        self._ensure_hookers()
        url = utils.to_url(url)

        if not hooker:
            hooker = TCPHooker(self)

        if not headers:
            headers = {}

        if json:
            if body:
                raise ValueError('body and json cannot be used together')

            body = _json.dumps(json)
            headers['Content-Type'] = 'application/json'

        elif body:
            if not isinstance(body, str):
                raise TypeError('body must be a string')

            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'text/plain'

        headers['Content-Length'] = len(body) if body else 0
        await hooker.connect(url)

        assert url.hostname is not None, 'url must have a hostname'
        headers.update(self.headers)
        request = hooker.build_request(
            method=method,
            host=url.hostname,
            path=url.path or '/',
            headers=headers,
            body=body
        )

        await hooker.write(request)
        response = await hooker.get_response()

        if not ignore_redirects:
            if 301 <= response.status <= 308:
                location = response.headers['Location']
                return await self._request(
                    url=location,
                    method=method,
                    headers=headers,
                    body=body,
                    json=json,
                )

        self._hookers.append(hooker)
        return response

    async def _connect(self, url: StrURL) -> WebSocket:
        url = utils.to_url(url)

        hooker = WebSocketHooker(self)
        websocket = await hooker.connect(url)

        self._hookers.append(hooker)
        return websocket

def request(url: StrURL, method: str, **kwargs: Any):
    client = HTTPSession(loop=kwargs.pop('loop', None))
    return client.request(url, method, **kwargs)

def ws_connect(url: str, **kwargs: Any):
    client = HTTPSession(loop=kwargs.pop('loop', None))
    return client.ws_connect(url, **kwargs)
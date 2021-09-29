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
import asyncio
from typing import Any, Dict, List, Optional
import json as _json

from .hooker import TCPHooker, WebsocketHooker, Websocket
from .response import HTTPResponse
from .utils import AsyncContextManager

from railway import compat

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

        session = http.HTTPSession()

        async def request():
            async with session.request('https://example.com/') as response:
                text = response.text()
                print(text)

                headers = response.headers
                print(headers)

        session.loop.run_until_complete(request())

    """
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        self.loop = loop or compat.get_event_loop()

        self._hookers: List[TCPHooker] = []

    def _ensure_hookers(self):
        for hooker in self._hookers:
            hooker.ensure()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc: Any):
        await self.close()
        return self

    async def close(self):
        for hooker in self._hookers:
            if not hooker.closed:
                await hooker.close()

    def request(self, method: str, url: str, **kwargs: Any):
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

            async with session.request('https://example.com/') as response:
                print(response.text())

            # or you could use it without a context manager

            response = await session.request('https://example.com/')
            print(response.text())

        """
        return AsyncContextManager(self._request(url, method, **kwargs))

    def ws_connect(self, url: str, **kwargs: Any) -> AsyncContextManager[Websocket]:
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
        return AsyncContextManager(self._connect(url)) # type: ignore

    def get(self, url: str, **kwargs: Any):
        return self.request('GET', url, **kwargs)

    def post(self, url: str, **kwargs: Any):
        return self.request('POST', url, **kwargs)

    def put(self, url: str, **kwargs: Any):
        return self.request('PUT', url, **kwargs)

    def delete(self, url: str, **kwargs: Any):
        return self.request('DELETE', url, **kwargs)

    def head(self, url: str, **kwargs: Any) :
        return self.request('HEAD', url, **kwargs)

    async def redirect(self, hooker: TCPHooker, response: HTTPResponse, method: str) -> HTTPResponse:
        copy = hooker.copy()
        await hooker.close()

        copy.connected = False
        location = response.headers['Location']

        return await self._request(location, method, hooker=copy)

    async def _request(self, 
                    url: str, 
                    method: str, 
                    *,
                    headers: Optional[Dict[str, Any]]=None,
                    body: Any=None,
                    json: Optional[Dict[str, Any]]=None,
                    ignore_redirects: bool=False, 
                    hooker: Optional[TCPHooker]=None):
        self._ensure_hookers()

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

        headers['Content-Lenght'] = len(body) if body else 0
        is_ssl, host, path = hooker.parse_host(url)

        if is_ssl:
           await hooker.create_ssl_connection(host)
        else:
            await hooker.create_connection(host)

        request = hooker.build_request(
            method=method,
            host=host,
            path=path,
            headers=headers,
            body=body
        )

        await hooker.write(request)
        response = await hooker.build_response()

        if not ignore_redirects:
            if 301 <= response.status <= 308:
                return await self.redirect(
                    hooker=hooker,
                    response=response,
                    method=method
                )

        self._hookers.append(hooker)
        await hooker.close()

        return response

    async def _connect(self, url: str) -> Optional[Websocket]:
        hooker = WebsocketHooker(self)
        is_ssl, host, path = hooker.parse_host(url)

        if is_ssl:
            websocket = await hooker.create_ssl_connection(host, path)
        else:
            websocket = await hooker.create_connection(host, path)

        self._hookers.append(hooker)
        return websocket

def request(url: str, method: str, **kwargs: Any):
    client = HTTPSession(kwargs.pop('loop', None))
    return client.request(url, method, **kwargs)

def ws_connect(url: str, **kwargs: Any):
    client = HTTPSession(kwargs.pop('loop', None))
    return client.ws_connect(url, **kwargs)
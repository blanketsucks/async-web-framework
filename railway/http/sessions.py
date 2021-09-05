import asyncio
from typing import Any, Dict, List, Optional
import json as _json

from .hooker import TCPHooker, WebsocketHooker, Websocket
from .response import Response
from .utils import AsyncContextManager

from railway import compat

__all__ = (
    'HTTPSession',
    'request',
    'ws_connect',
)

class HTTPSession:
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        self.loop = loop or compat.get_running_loop()

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
        return AsyncContextManager(self._request(url, method, **kwargs))

    def ws_connect(self, url: str, **kwargs: Any) -> AsyncContextManager[Optional[Websocket]]:
        return AsyncContextManager(self._connect(url))

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

    async def redirect(self, hooker: TCPHooker, response: Response, method: str) -> Response:
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
    return client.request(url, method)

def ws_connect(url: str, **kwargs: Any):
    client = HTTPSession(kwargs.pop('loop', None))
    return client.ws_connect(url, **kwargs)
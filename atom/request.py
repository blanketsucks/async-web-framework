from __future__ import annotations
import json
from typing import TYPE_CHECKING, Union, Dict, Optional, Any
import urllib.parse

from .objects import Route, WebsocketRoute
from .response import Response
from .utils import find_headers
from .cookies import CookieJar
from .datastructures import URL
from .sessions import CookieSession
from .abc import AbstractApplication, AbstractProtocol
from .responses import redirects

__all__ = (
    'Request',
)

class Request:
    __slots__ = (
        '_encoding', 'version', 'method',
        '_url', 'headers', '_body', 'protocol', 'connection_info',
        '_cookies', 'route', '_app'
    )

    def __init__(self,
                method: str,
                url: str,
                headers: Dict[str, str],
                protocol: AbstractProtocol,
                version: str,
                body: str,
                app: AbstractApplication):
        self._encoding = "utf-8"
        self._app = app
        self._url = url
        self._body = body
        self.version = version
        self.method = method
        self.headers = headers
        self.protocol = protocol
        self.route: Union[Route, WebsocketRoute] = None

    @property
    def app(self):
        return self._app

    @property
    def url(self) -> URL:
        return URL(self._url)

    @property
    def cookies(self) -> Dict[str, str]:
        jar = self.cookie_jar
        self._cookies = {
            cookie.name: cookie.value for cookie in jar
        }

        return self._cookies

    @property
    def cookie_jar(self):
        return CookieJar.from_request(self)

    @property
    def session(self):
        return CookieSession.from_request(self)

    @property
    def user_agent(self):
        return self.headers.get('User-Agent')

    @property
    def host(self):
        return self.headers.get('Host')

    @property
    def connection(self):
        return self.headers.get('Connection')

    @property
    def query(self):
        return self.url.query

    def text(self) -> str:
        return self._body.decode() if isinstance(self._body, (bytes, bytearray)) else self._body

    def json(self) -> Dict[str, Any]:
        return json.loads(self.text())

    def redirect(self, to: str, body: Any=None, headers: Dict=None, status: int=None, content_type: str=None):
        headers = headers or {}
        status = status or 302
        content_type = content_type or 'text/plain'

        url = urllib.parse.quote_plus(to, ":/%#?&=@[]!$&'()*+,;")
        cls = redirects.get(status)

        if not cls:
            ret = f'{status} is not a valid redirect status code'
            raise ValueError(ret)

        response = cls(location=url, body=body, headers=headers, content_type=content_type)
        return response

    @classmethod
    def parse(cls, data: bytes, protocol: AbstractProtocol):
        headers, body = find_headers(data)
        line, = next(headers)

        parts = line.split(' ')
        headers = dict(headers)
        
        method = parts[0]
        version = parts[2]
        path = parts[1]

        self = cls(
            method=method,
            url=path,
            version=version,
            protocol=protocol,
            headers=headers,
            body=body,
            app=protocol.app
        )

        return self

    def __repr__(self) -> str:
        return '<Request url={0.url.path!r} method={0.method!r} version={0.version!r} ' \
               'headers={0.headers!r}>'.format(self)

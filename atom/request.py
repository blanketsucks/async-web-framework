import json
import typing
import yarl
import asyncio
from http.cookies import SimpleCookie
from multidict import CIMultiDict

if typing.TYPE_CHECKING:
    from .server import ConnectionInfo, HTTPProtocol, WebsocketProtocol
    from .app import Application

class Header(CIMultiDict):
    def get_all(self, key):
        return self.getall(key, default=[])

class Request:
    __slots__ = (
        '_encoding', 'version', 'status_code', 'method',
        'url', 'headers', 'body', 'protocol', 'connection_info',
        '_cookies',
    )

    def __init__(self,
                method: str,
                url: bytes,
                status_code: int,
                headers: typing.Dict,
                protocol: typing.Union['HTTPProtocol', 'WebsocketProtocol'],
                connection_info: 'ConnectionInfo',
                version: str=None, 
                body=None):

        self._encoding = "utf-8"

        self.version = version
        self.status_code = status_code
        self.method = method
        self.url = yarl.URL(url)
        self.headers = Header(headers)
        self.body = body
        self.protocol = protocol
        self.connection_info = connection_info

    @property
    def cookies(self):
        cookie = self.headers.get('Cookie', None)

        if cookie:
            cookies = SimpleCookie()
            cookies.load(cookie)

            self._cookies = {
                    name: cookie.value for name, cookie in cookies.items()
                }
        else:
            self._cookies = {}

        return self._cookies

    @property
    def token(self):
        prefixes = ('Bearer',)
        auth: str = self.headers.get('Authorization', None)

        if auth:
            prefix, token = auth.split(' ', maxsplit=1)
            if prefix not in prefixes:
                return None

            return token

        return None

    @property
    def ssl(self):
        return self.connection_info.ssl

    @property
    def peername(self):
        return self.connection_info.peername

    @property
    def socket(self):
        return self.connection_info.socket

    @property
    def port(self):
        return self.connection_info.client_port

    @property
    def ip(self):
        return self.connection_info.client

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
    def params(self):
        return self.url.query

    def text(self):
        if self.body:
            return self.body.decode(self._encoding)

        return None

    def json(self, **kwargs):
        text = self.text()

        if text:
            return json.loads(text, **kwargs)
        return None

    def __repr__(self) -> str:
        return '<Request url={0.url.raw_path} method={0.method}>'.format(self)
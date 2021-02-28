import json
import typing
import yarl
from http.cookies import SimpleCookie
from multidict import CIMultiDict
import aiohttp

if typing.TYPE_CHECKING:
    from .server import ConnectionInfo, HTTPProtocol, WebsocketProtocol

__all__ = (
    'Headers',
    'Request'
)

class _RequestContextManager:
    def __init__(self, session: aiohttp.ClientSession, url: str, method: str, **kwargs) -> None:
        self.__session = session

        self.url = url
        self.method = method
        self.kwargs = kwargs

    async def __aenter__(self):
        method = self.method
        url = self.url
        kwargs = self.kwargs

        async with self.__session.request(method, url, **kwargs) as resp:
            return resp

    async def __aexit__(self, _type, value, tb):
        await self.__session.close()
        return self

class Headers(CIMultiDict):
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

        self.version = version[:-1]
        self.status_code = status_code
        self.method = method
        self.url = yarl.URL(url)
        self.headers = Headers(headers)
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
        return '<Request url={0.url.raw_path!r} method={0.method!r} status={0.status_code} version={0.version!r} '\
                'headers={0.headers} socket={0.socket} ssl={0.ssl} protocol={0.protocol} cookies={0.cookies}>'.format(self)
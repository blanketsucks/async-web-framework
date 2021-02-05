import json
import typing
import yarl
import asyncio

class Request:
    __slots__ = (
        '_encoding', 'version', 'status_code', 'method',
        'url', 'headers', 'body', 'transport'
    )

    def __init__(self, method: str, url: bytes, status_code,
                headers: typing.Dict, transport: asyncio.BaseTransport,
                version: str=None, body=None):

        self._encoding = "utf-8"

        self.version = version
        self.status_code = status_code
        self.method = method
        self.url = yarl.URL(url)
        self.headers = headers
        self.body = body
        self.transport = transport

    @property
    def user_agent(self):
        value = self.headers.get('User-Agent')
        return {
            'User-Agent': value
        }

    @property
    def host(self):
        value = self.headers.get('Host')
        return {
            'Host': value
        }

    @property
    def connection(self):
        value = self.headers.get('Connection')
        return {
            'Connection': value
        }

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
    
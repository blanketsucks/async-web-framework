from atom.datastructures import HTTPHeaders, URL

import typing
import json as _json
from collections import namedtuple

__all__ = (
    'Request',
    'Response'
)

class Request:
    protocol = '1.1'

    def __init__(self,
                url: URL,
                path: str, 
                method: str, 
                hostname: str, 
                headers: HTTPHeaders,
                json: typing.Dict) -> None:
        
        self.url = url
        self.path = path
        self.method = method
        self.hostname = hostname
        self.headers = headers
        self.json = json

    def __str__(self) -> str:   
        messages = [
            f'{self.method} {self.path} HTTP/{self.protocol}',
            f'Host: {self.hostname}'
        ]
        dumped = _json.dumps(self.json)

        if self.json:
            messages.append('Content-Type: application/json')
            messages.append(f'Content-Lenght: {len(dumped)}')

        message = '\r\n'.join(messages) + '\r\n'
        message += self.headers.__str__()
        message += '\r\n'

        if self.json:
            message += dumped

        return message

    def encode(self):
        return str(self).encode()


class Response:
    def __init__(self, data: bytes) -> None:
        self._data = data

        self._body = None
        self._parse()

    @property
    def status(self):
        return int(self._status.decode())

    @property
    def headers(self) -> HTTPHeaders:
        raw = self.raw_headers
        new = HTTPHeaders()

        for key, value in raw.items():
            actual = key.decode()
            new[actual] = value.decode() if isinstance(value, bytes) else value
        
        return new

    @property
    def raw_headers(self) -> HTTPHeaders:
        return self._headers

    @property
    def raw_body(self) -> bytes:
        return self._body

    @property
    def raw(self):
        return self._data

    @property
    def message(self):
        return self._resp_message.decode(self.headers.get_encoding())

    def _parse(self):
        items = self._data.split(b'\r\n')
        items = [item for item in items if len(item) > 2]
        
        copy = items.copy()
        copy.reverse()

        self._body = copy[0]
        items.remove(self._body)

        self._protocol, self._status, self._resp_message = items[0].split(b' ', maxsplit=2)
        items.remove(items[0])

        headers = HTTPHeaders()

        for item in items:
            info = item.split(b': ', 1)
            if len(info) < 2:
                continue

            name, value = info
            headers[name] = value

        self._headers = headers
        return self

    async def text(self, *, encoding: str=...):
        if self._body:
            encoding = self.headers.get_encoding() if encoding is ... else encoding
            return self._body.decode(encoding)

        return ''

    async def json(self, *, encoding: str=...) -> typing.Dict:
        text = await self.text(encoding=encoding)
        return _json.loads(text)
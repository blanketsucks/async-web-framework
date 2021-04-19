
from .sockets import HTTPStatus

import typing
import json

__all__ = (
    'Response',
    'HTMLResponse',
    'JSONResponse',
)


class Response:
    def __init__(self, 
                body: str=...,
                status: int=...,
                content_type: str=...,
                headers: typing.Dict[str, str]=...,
                version: str=...):

        if body is ...:
            body = ''

        self.version = '1.1' if version is ... else version
        self._status = 200 if status is ... else status
        self._body = body
        self._content_type = 'text/plain' if content_type is ... else content_type
        self._encoding = "utf-8"

        if headers is ...:
            headers = {}

        self._headers = headers

        if body:
            self._headers['Content-Type'] = content_type
            self._headers['Content-Lenght'] = len(body)

    @property
    def body(self):
        return self._body

    @property
    def status(self):
        return self._status

    @property
    def content_type(self):
        return self._content_type

    @property
    def headers(self):
        return self._headers

    def add_body(self, data: str):
        self._body += data

    def add_header(self, key: str, value: str):
        self._headers[key] = value

    def __repr__(self) -> str:
        fmt = '<Response body={0.body!r} content_type={0.content_type!r} status={0.status} version={0.version}>'
        return fmt.format(self)

    def encode(self):
        status = HTTPStatus(self._status)

        response = [f'HTTP/{self.version} {status} {status.description}']

        response.extend(f'{k}: {v}' for k, v in self.headers.items())
        response.append('\r\n')

        response = b'\r\n'.join(part.encode() for part in response)
        if self.body:
            response += self._body.encode()

        return response

class HTMLResponse(Response):
    def __init__(self, 
                body: str=...,
                status: int=...,
                headers: typing.Dict[str, str]=...,
                version: str=...):

        super().__init__(
            body=body, 
            status=status, 
            content_type='text/html', 
            headers=headers, 
            version=version
        )


class JSONResponse(Response):
    def __init__(self, 
                body: typing.Union[typing.Dict, typing.List]=..., 
                status: int=..., 
                headers: typing.Dict[str, str]=..., 
                version: str=...):

        if body is ...:
            body = {}

        super().__init__(
            body=json.dumps(body), 
            status=status, 
            content_type='application/json', 
            headers=headers, 
            version=version
        )

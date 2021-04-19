import typing

from . import utils

class Request:
    def __init__(self,
                *,
                method: str,
                path: str,
                version: str,
                body: str=...,
                content_type: str=...,
                headers: typing.Dict[str, str]=...) -> None:
        
        if body is ...:
            body = ''

        if headers is ...:
            headers = {}

        if content_type is ...:
            content_type = 'text/plain'

        self.body = body
        self.headers = headers
        self.content_lenght = len(body)
        self.content_type = content_type
        self.method = method
        self.version = version
        self.path = path

        if self.body:
            self.headers['Content-Type'] = self.content_type
            self.headers['Content-Lenght'] = self.content_lenght

    def encode(self):
        request = [f'{self.method} {self.path} HTTP/{self.version}']

        request.extend(f'{k}: {v}' for k, v in self.headers.items())
        request.append('\r\n')

        request = b'\r\n'.join(part.encode() for part in request)
        if self.body:
            request += self.body.encode()

        return request

    @classmethod
    def parse(cls, data: bytes):
        headers, body = utils.find_headers(data)
        line, = next(headers)

        parts = line.split(' ')
        headers = dict(headers)

        method = parts[0]
        version = parts[2]
        path = parts[1]
        
        return cls(
            method=method,
            path=path,
            version=version,
            headers=headers,
            body=body
        )
         
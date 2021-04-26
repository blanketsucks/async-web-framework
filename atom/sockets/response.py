import typing

from .enums import HTTPStatus
from . import utils

class Response:
    def __init__(self,
                *,
                body: str=...,
                status: HTTPStatus=...,
                version: str=...,
                headers: typing.Dict[str, str]=...) -> None:
        
        self.body = utils.check_ellipsis(body, '')
        self.status = utils.check_ellipsis(status, HTTPStatus.OK)
        self.version = utils.check_ellipsis(version, '1.1')
        self.headers = utils.check_ellipsis(headers, {})

    def encode(self):
        response = [f'HTTP/{self.version} {self.status} {self.status.description}']

        response.extend(f'{k}: {v}' for k, v in self.headers.items())
        response.append('\r\n')

        response = b'\r\n'.join(part.encode() for part in response)
        if self.body:
            response += self.body.encode()

        return response

    @classmethod
    def parse(cls, data: bytes):
        headers, body = utils.find_headers(data)
        line, = next(headers)

        parts = line.split(' ', maxsplit=2)
        headers = dict(headers)

        version: str = parts[0]
        status: int = parts[1]

        return cls(
            status=HTTPStatus(int(status)),
            version=version,
            body=body,
            headers=headers
        )
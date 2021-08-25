from __future__ import annotations
import typing
import json

from atom.response import HTTPStatus

if typing.TYPE_CHECKING:
    from .hooker import TCPHooker

class Response:
    def __init__(self,
                *,
                hooker: TCPHooker, 
                status: HTTPStatus,
                version: str, 
                headers: typing.Dict[str, str], 
                body: bytes=None) -> None:
        self._hooker = hooker

        self.status = status
        self.version = version
        self.headers = headers

        self._body = body

    async def read(self):
        if not self._body:
            self._body = await self._hooker._read_body()

        return self._body

    async def text(self) -> str:
        body = await self.read()
        return body

    async def json(self) -> typing.Dict[str, typing.Any]:
        text = await self.text()
        return json.loads(text)
from __future__ import annotations
from typing import Any, Dict, Optional, Union, TYPE_CHECKING
import json

from railway.response import HTTPStatus

if TYPE_CHECKING:
    from .abc import Hooker
    from .hooker import TCPHooker

class Response:
    def __init__(self,
                *,
                hooker: Union[TCPHooker, Hooker], 
                status: HTTPStatus,
                version: str, 
                headers: Dict[str, Any], 
                body: Optional[bytes]=None) -> None:
        self._hooker = hooker

        self.status = status
        self.version = version
        self.headers = headers

        self._body: Optional[bytes] = body

    async def read(self) -> bytes:
        body = self._body

        if not body:
            self._body = body = await self._hooker._read_body() # type: ignore

        return body # type: ignore

    async def text(self) -> str:
        body = await self.read()
        return body.decode()

    async def json(self) -> Dict[str, Any]:
        text = await self.text()
        return json.loads(text)
"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Union, TYPE_CHECKING
import json

from railway.response import HTTPStatus

if TYPE_CHECKING:
    from .abc import Hooker
    from .hooker import TCPHooker

class HTTPResponse:
    """
    An HTTP Response.

    Attributes
    ----------
    status: :class:`railway.response.HTTPStatus`
        The status of the response.
    version: :class:`str`
        The HTTP version of the response.
    headers: :class:`dict`
        The headers of the response.
    """
    def __init__(self,
                *,
                hooker: Union[TCPHooker, Hooker], 
                status: HTTPStatus,
                version: str, 
                headers: Dict[str, Any], 
                body: bytes) -> None:
        self._hooker = hooker

        self.status = status
        self.version = version
        self.headers = headers

        self._body: bytes = body

    def read(self) -> bytes:
        """
        The raw body of the response.
        """
        return self._body

    def text(self) -> str:
        """
        The body of the response as a string.
        """
        body = self.read()
        return body.decode()

    def json(self) -> Dict[str, Any]:
        """
        The body of the response as a JSON object.
        """
        text = self.text()
        return json.loads(text)
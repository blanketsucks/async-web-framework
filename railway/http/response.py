from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING

from railway import HTTPStatus
from railway.headers import Headers
from railway.streams import StreamReader
from railway.request import HTTPConnection

if TYPE_CHECKING:
    from .abc import Hooker


class HTTPResponse(HTTPConnection):
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
    def __init__(
        self,
        *,
        hooker: Hooker,
        status: HTTPStatus,
        version: str,
        headers: Dict[str, str],
    ) -> None:
        self._hooker = hooker

        self.status = status
        self.version = version
        self.headers = Headers(headers)

        self._body: bytes = b''

    @property
    def hooker(self) -> Hooker:
        """
        The hooker that created this response.
        """
        return self._hooker

    @property
    def charset(self) -> Optional[str]:
        """
        The charset of the response.
        """
        return self.headers.charset

    @property
    def content_type(self) -> Optional[str]:
        """
        The content type of the response.
        """
        return self.headers.content_type

    def get_reader(self) -> StreamReader:
        assert self.hooker.reader is not None
        return self.hooker.reader

    def is_closed(self) -> bool:
        """
        Whether the response is closed.
        """
        return self.hooker.closed

    async def close(self) -> None:
        """
        Close the response.
        """
        await self.hooker.close()
from __future__ import annotations
import io
from typing import Iterable, List, Optional, TYPE_CHECKING, Tuple, TypeVar

from .utils import find_headers
from .file import File

if TYPE_CHECKING:
    from .request import Request

T = TypeVar('T')

def _get(iterable: Iterable[T], index: int) -> Optional[T]:
    try:
        return iterable[index]
    except IndexError:
        return None

class Disposition:
    def __init__(self, header: str) -> None:
        self.header = header
        self._parts = self.header.split('; ')

    @property
    def content_type(self):
        return self._parts[0]

    @property
    def name(self):
        return _get(self._parts, 1)

    @property
    def filename(self):
        return _get(self._parts, 2)

class FormData:
    def __init__(self) -> None:
        self.files: List[Tuple[File, Disposition]] = []

    def __iter__(self):
        return iter(self.files)

    def add_file(self, file: File, disposition: Disposition) -> None:
        self.files.append((file, disposition))

    @classmethod
    def from_request(cls, request: Request) -> FormData:
        form = cls()
        data = request.text()

        content_type = request.headers.get('Content-Type')
        if not content_type:
            return form
        
        ct, boundary = content_type.split('; ')
        boundary = '--' + boundary.strip('boundary=')

        data = data.strip(boundary + '--\r\n')
        split = data.split(boundary + '\r\n')
        
        for part in split:
            if part:
                headers, body = find_headers(part.encode())
                headers = dict(headers)

                disposition = Disposition(headers.get('Content-Disposition'))

                data = io.BytesIO(body)
                file = File(data)

                form.add_file(file, disposition)

        return form
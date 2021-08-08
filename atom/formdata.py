from __future__ import annotations
from typing import List, TYPE_CHECKING, Tuple

from .file import File

if TYPE_CHECKING:
    from .request import Request

class FormData:
    def __init__(self) -> None:
        self.files: List[Tuple[File, str, str]] = []

    def add_file(self, file: File, name: str, content_type: str) -> None:
        self.files.append((file, name, content_type))

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
        
        return split



        
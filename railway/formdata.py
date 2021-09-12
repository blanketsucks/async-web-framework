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
import io
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple, TypeVar

from .utils import find_headers
from .file import File

if TYPE_CHECKING:
    from .request import Request

T = TypeVar('T')

__all__ = (
    'Disposition',
    'FormData'
)

def _get(iterable: List[T], index: int) -> Optional[T]:
    try:
        return iterable[index]
    except IndexError:
        return None

class Disposition:
    """
    A Content-Disposition header.
    """
    def __init__(self, header: str) -> None:
        self.header = header
        self._parts = self.header.split('; ')

    @property
    def content_type(self) -> str:
        """
        The content type.
        """
        return self._parts[0]

    @property
    def name(self) -> Optional[str]:
        """
        The name of the disposition.
        """
        return _get(self._parts, 1)

    @property
    def filename(self) -> Optional[str]:
        """
        The filename of the disposition.
        """
        return _get(self._parts, 2)

class FormData:
    """
    A form data object.

    Attributes
    ----------
    files: List[Tuple[:class:`~railway.file.File`, Optional[:class:`~railway.formdata.Disposition`]]]
        A list of tuples containing a :class:`~railway.file.File and :class:`~railway.formdata.Disposition` objects.
    """
    def __init__(self) -> None:
        self.files: List[Tuple[File, Optional[Disposition]]] = []

    def __iter__(self):
        return iter(self.files)

    def add_file(self, file: File, disposition: Optional[Disposition]) -> None:
        """
        Add a file to the form data.

        Parameters
        ----------
        file: :class:`~railway.file.File`
            A file object.
        disposition: :class:`~railway.formdata.Disposition`
            A disposition object.
        """
        self.files.append((file, disposition))

    @classmethod
    def from_request(cls, request: 'Request') -> FormData:
        """
        Creates a form data object from a request.

        Parameters
        ----------
        request: :class:`~railway.request.Request`
            a request.
        """
        form = cls()
        data = request.text()

        content_type = request.headers.get('Content-Type')
        if not content_type:
            return form
        
        _, boundary = content_type.split('; ')
        boundary = '--' + boundary.strip('boundary=')

        data = data.strip(boundary + '--\r\n')
        split = data.split(boundary + '\r\n')
        
        for part in split:
            if part:
                try:
                    hdrs, body = find_headers(part.encode())
                    headers: Dict[str, str] = dict(hdrs) # type: ignore

                    content = headers.get('Content-Disposition')
                    if content:
                        disposition = Disposition(content)
                        filename = disposition.filename
                    else:
                        disposition = None
                        filename = None

                    data = io.BytesIO(body)
                    file = File(data, filename=filename)

                    form.add_file(file, disposition)
                except ValueError:
                    continue

        return form
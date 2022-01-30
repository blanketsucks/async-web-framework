from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, TYPE_CHECKING, Tuple, TypeVar
import string
import random

from .files import File
from .utils import clean_values, parse_http_data, CLRF

if TYPE_CHECKING:
    from .app import Application
    from .request import Request

T = TypeVar('T')

BOUNDARY_LIMITER = b'--'

__all__ = (
    'Disposition',
    'FormData'
)

def _get(iterable: List[T], index: int) -> Optional[T]:
    try:
        return iterable[index]
    except IndexError:
        return None

def parse_field(text: str) -> str:
    _, _1, value = text.partition('=')
    return value.strip('"').strip("'")

class DispositionNotFound(Exception):
    pass

class InvalidDisposition(Exception):
    pass

class FormDataField(NamedTuple):
    file: File
    headers: Dict[str, str]
    dispotision: Disposition

class Disposition:
    """
    A Content-Disposition header.
    """
    def __init__(self, *, name: str, filename: Optional[str]=None, content_type: Optional[str]=None) -> None:
        self.content_type = content_type or 'application/octet-stream'
        self.name = name
        self.filename = filename
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Disposition:
        """
        Create a Disposition object from a Content-Disposition header.

        Parameters
        ----------
        headers: :class:`dict`
            A dictionary of headers.

        Returns
        -------
        :class:`~subway.formdata.Disposition`
            A Disposition object.
        """
        disposition = headers.get('Content-Disposition')
        if not disposition:
            raise DispositionNotFound('Content-Disposition header not found.')

        disposition = disposition.split('; ')
        if disposition[0] != 'form-data':
            raise InvalidDisposition('Invalid Content-Disposition header.')

        name = parse_field(disposition[1])
        filename = _get(disposition, 2)

        if filename:
            filename = parse_field(filename)

        content_type = headers.get('Content-Type')
        return cls(name=name, filename=filename, content_type=content_type)

    def to_header(self) -> str:
        """
        Create a Content-Disposition header.

        Returns
        -------
        :class:`str`
            A Content-Disposition header.
        """
        header = f'form-data; name={self.name!r}'
        if self.filename:
            header += f'; filename={self.filename!r}'
        return header

class FormData(Dict[str, FormDataField]):
    """
    A form data object.

    Attributes
    ----------
    files: List[Tuple[:class:`~subway.file.File`, :class:`~subway.formdata.Disposition`]]
        A list of tuples containing a :class:`~subway.file.File and :class:`~subway.formdata.Disposition` objects.
    """
    def __init__(self) -> None:
        self._boundary: Optional[bytes] = None

    @classmethod
    async def from_request(cls, request: Request[Application]):
        """
        Creates a form data object from a request.

        Parameters
        ----------
        request: :class:`~subway.request.Request`
            a request.
        """
        form = cls()
        data = await request.read()

        content_type = request.headers.get('Content-Type')
        if not content_type:
            return form
        
        _, boundary = content_type.split('; ')
        boundary = ('--' + boundary.strip('boundary=')).encode()

        data = data.strip(boundary + b'--\r\n').split(boundary + b'\r\n')        
        for value in clean_values(data):
            try:
                result = parse_http_data(value, strip_status_line=False)
                disposition = Disposition.from_headers(result.headers)

                file = File(result.body)
                field = FormDataField(file=file, headers=result.headers, dispotision=disposition)

                form.add_field(field)
            except ValueError:
                continue

        form.boundary = boundary
        return form

    @property
    def boundary(self) -> Optional[bytes]:
        """
        The boundary string.

        Returns
        -------
        :class:`str`
            The boundary string.
        """
        return self._boundary

    @boundary.setter
    def boundary(self, boundary: bytes) -> None:
        self._boundary = boundary

    def generate_boundary(self) -> bytes:
        """
        Generate a boundary string.

        Returns
        -------
        :class:`str`
            The boundary string.
        """
        length = random.randint(1, 70)
        return ''.join([random.choice(string.ascii_letters) for _ in range(length)]).encode()
    
    def add_field(self, field: FormDataField) -> None:
        """
        Add a file to the form data.

        Parameters
        ----------
        file: :class:`~subway.file.File`
            A file object.
        disposition: :class:`~subway.formdata.Disposition`
            A disposition object.
        """
        self[field.dispotision.name] = field

    async def _prepare_field(self, field: FormDataField) -> bytes:
        assert self.boundary is not None, 'Boundary not set'
        disposition = field.dispotision

        boundary = BOUNDARY_LIMITER + self.boundary
        headers = [
            f'Content-Disposition: {disposition.to_header()}'.encode(),
            f'Content-Type: {disposition.content_type}'.encode(),
        ]

        body = boundary

        body += CLRF.join(headers) + (CLRF * 2)
        body += await field.file.read() + CLRF

        return body

    async def prepare(self) -> Tuple[bytearray, str]:
        self.boundary = boundary = self.generate_boundary()
        content_type = f'multipart/form-data; boundary={boundary}'

        body = bytearray()

        for field in self.values():
            chunk = await self._prepare_field(field)
            body.extend(chunk)


        body.extend(BOUNDARY_LIMITER + boundary + BOUNDARY_LIMITER)
        return body, content_type
            
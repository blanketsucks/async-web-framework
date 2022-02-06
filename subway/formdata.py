from __future__ import annotations

from typing import IO, Any, Dict, List, NamedTuple, Optional, TYPE_CHECKING, Tuple, TypeVar, Union
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
    'FormData',
    'FormDataField'
)

def _get(iterable: List[T], index: int) -> Optional[T]:
    try:
        return iterable[index]
    except IndexError:
        return None

def parse_field(text: str) -> str:
    _, __, value = text.partition('=')
    return value.strip('"').strip("'")

class DispositionNotFound(Exception):
    pass

class InvalidDisposition(Exception):
    pass

class FormDataField(NamedTuple):
    """
    A named tuple representing a form data field.

    Attributes
    ----------
    file: :class:`~.File`
        The file object.
    headers: :class:`dict`
        The headers of the field.
    disposition: :class:`~.Disposition`
        The disposition of the field.
    """
    file: File
    headers: Dict[str, str]
    disposition: Disposition

    @property
    def name(self) -> str:
        return self.disposition.name

    @property
    def filename(self) -> Optional[str]:
        return self.disposition.filename

    @property
    def content_type(self) -> str:
        return self.disposition.content_type

class Disposition:
    """
    A Content-Disposition header.

    Parameters
    ----------
    name: :class:`str`
        The name of the field.
    filename: Optional[:class:`str`]
        The filename of the field.
    content_type: Optional[:class:`str`]
        The content type of the field. Defaults to ``application/octet-stream``.
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
        header = f'form-data; name="{self.name}"'
        if self.filename:
            header += f'; filename="{self.filename}"'
        return header

class FormData(Dict[str, FormDataField]):
    """
    A form data object.
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
                field = FormDataField(file=file, headers=result.headers, disposition=disposition)

                form[field.name] = field
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
    
    def add_field(
        self, 
        file: Union[File, IO[bytes]],
        *,
        name: Optional[str] = None, # type: ignore
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> FormDataField:
        """
        Add a file to the form data.

        Parameters
        ----------
        file: Union[:class:`~.File`, :class:`io.IOBase`]
            The file object.
        name: Optional[:class:`str`]
            The name of the field.
        filename: Optional[:class:`str`]
            The filename of the field.
        content_type: Optional[:class:`str`]
            The content type of the field. Defaults to ``application/octet-stream``.
        headers: Optional[:class:`dict`]
            The headers of the field.
        """
        if not isinstance(file, File):
            file = File(file)

        assert file.filename or name, 'A file name or disposition name must be provided'
        name = name or file.filename # type: Any
        headers = headers or {}

        disposition = Disposition(name=name, filename=filename, content_type=content_type)
        field = FormDataField(file=file, headers=headers, disposition=disposition)

        self[field.name] = field
        return field

    async def _prepare_field(self, field: FormDataField) -> bytes:
        assert self.boundary is not None, 'Boundary not set'
        disposition = field.disposition

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
        """
        Prepare the form data for sending.
        """
        self.boundary = boundary = self.generate_boundary()
        content_type = f'multipart/form-data; boundary={boundary}'

        body = bytearray()

        for field in self.values():
            chunk = await self._prepare_field(field)
            body.extend(chunk)

        body.extend(BOUNDARY_LIMITER + boundary + BOUNDARY_LIMITER)
        return body, content_type
            
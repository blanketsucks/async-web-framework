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
from typing import Any, Dict, List, Union, Optional
import json
import enum
import mimetypes

from .cookies import CookieJar
from .file import File
from .datastructures import MultiDict

__all__ = (
    'Response',
    'HTTPStatus',
    'HTMLResponse',
    'JSONResponse',
    'FileResponse',
)

class HTTPStatus(enum.IntEnum):
    _description_: str
    
    def __new__(cls, value: int, description: str):
        self = int.__new__(cls, value)

        self._value_ = value
        self._description_ = description
        self.__doc__ = description

        return self

    @property
    def status(self):
        return self.value

    @property
    def description(self):
        return self._description_

    CONTINUE = 100, 'Continue'
    SWITCHING_PROTOCOLS = 101, 'Switching Protocols'
    PROCESSING = 102, 'Processing'
    EARLY_HINTS = 103, 'Early Hints'
    OK = 200, 'OK'
    CREATED = 201, 'Created'
    ACCEPTED = 202, 'Accepted'
    NON_AUTHORITATIVE_INFORMATION = 203, 'Non-Authoritative Information'
    NO_CONTENT = 204, 'No Content'
    RESET_CONTENT = 205, 'Reset Content'
    PARTIAL_CONTENT = 206, 'Partial Content'
    MULTI_STATUS = 207, 'Multi-Status'
    ALREADY_REPORTED = 208, 'Already Reported'
    IM_USED = 226, 'IM Used'
    MULTIPLE_CHOICES = 300, 'Multiple Choices'
    MOVED_PERMANENTLY = 301, 'Moved Permanently'
    FOUND = 302, 'Found'
    SEE_OTHER = 303, 'See Other'
    NOT_MODIFIED = 304, 'Not Modified'
    USE_PROXY = 305, 'Use Proxy'
    TEMPORARY_REDIRECT = 307, 'Temporary Redirect'
    PERMANENT_REDIRECT = 308, 'Permanent Redirect'
    BAD_REQUEST = 400, 'Bad Request'
    UNAUTHORIZED = 401, 'Unauthorized'
    PAYMENT_REQUIRED = 402, 'Payment Required'
    FORBIDDEN = 403, 'Forbidden'
    NOT_FOUND = 404, 'Not Found'
    METHOD_NOT_ALLOWED = 405, 'Method Not Allowed'
    NOT_ACCEPTABLE = 406, 'Not Acceptable'
    PROXY_AUTHENTICATION_REQUIRED = 407, 'Proxy Authentication Required'
    REQUEST_TIMEOUT = 408, 'Request Timeout'
    CONFLICT = 409, 'Conflict'
    GONE = 410, 'Gone'
    LENGTH_REQUIRED = 411, 'Length Required'
    PRECONDITION_FAILED = 412, 'Precondition Failed'
    REQUEST_ENTITY_TOO_LARGE = 413, 'Request Entity Too Large'
    REQUEST_URI_TOO_LONG = 414, 'Request-URI Too Long'
    UNSUPPORTED_MEDIA_TYPE = 415, 'Unsupported Media Type'
    REQUESTED_RANGE_NOT_SATISFIABLE = 416, 'Requested Range Not Satisfiable'
    EXPECTATION_FAILED = 417, 'Expectation Failed'
    IM_A_TEAPOT = 418, 'I\'m a Teapot'
    MISDIRECTED_REQUEST = 421, 'Misdirected Request'
    UNPROCESSABLE_ENTITY = 422, 'Unprocessable Entity'
    LOCKED = 423, 'Locked'
    FAILED_DEPENDENCY = 424, 'Failed Dependency'
    TOO_EARLY = 425, 'Too Early'
    UPGRADE_REQUIRED = 426, 'Upgrade Required'
    PRECONDITION_REQUIRED = 428, 'Precondition Required'
    TOO_MANY_REQUESTS = 429, 'Too Many Requests'
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431, 'Request Header Fields Too Large'
    UNAVAILABLE_FOR_LEGAL_REASONS = 451, 'Unavailable For Legal Reasons'
    INTERNAL_SERVER_ERROR = 500, 'Internal Server Error'
    NOT_IMPLEMENTED = 501, 'Not Implemented'
    BAD_GATEWAY = 502, 'Bad Gateway'
    SERVICE_UNAVAILABLE = 503, 'Service Unavailable'
    GATEWAY_TIMEOUT = 504, 'Gateway Timeout'
    HTTP_VERSION_NOT_SUPPORTED = 505, 'HTTP Version Not Supported'
    VARIANT_ALSO_NEGOTIATES = 506, 'Variant Also Negotiates'
    INSUFFICIENT_STORAGE = 507, 'Insufficient Storage'
    LOOP_DETECTED = 508, 'Loop Detected'
    NOT_EXTENDED = 510, 'Not Extended'
    NETWORK_AUTHENTICATION_REQUIRED = 511, 'Network Authentication Required'


class Response:
    """
    A class that is used to build a response that is later sent to the client.

    Parameters
    ----------
    body: :class:`str`
        The body of the response.
    status: :class:`int`
        The status code of the response.
    content_type: :class:`str`
        The content type of the response.
    headers: :class:`dict`
        The headers of the response.
    version: :class:`str`
        The HTTP version of the response.

    Attributes
    ----------
        version: :class:`str`
            The HTTP version of the response.
        cookies: :class:`~railway.cookies.CookieJar`
            A cookie jar that contains all the cookies that should be set on the response.
    """
    def __init__(self, 
                body: Optional[str]=None,
                status: Optional[int]=None,
                content_type: Optional[str]=None,
                headers: Optional[Dict[str, Any]]=None,
                version: Optional[str]=None):
        self.version: str = version or '1.1'
        self._status = HTTPStatus(status or 200) # type: ignore
        self._body = body or ''
        self._content_type = content_type or 'text/html'
        self._encoding = "utf-8"

        if not headers:
            headers = {}

        self._headers: MultiDict[str, Any] = MultiDict(headers)

        if body:
            self._headers['Content-Type'] = content_type
            self._headers['Content-Lenght'] = len(body)

        self.cookies: CookieJar = CookieJar()

    @property
    def body(self) -> Any:
        """
        The body of the response.
        """
        return self._body

    @body.setter
    def body(self, value):
        self._body = value

        self._headers['Content-Type'] = self.content_type
        self._headers['Content-Length'] = len(value)

    @property
    def status(self) -> HTTPStatus:
        """
        The status code of the response.
        """
        return self._status

    @property
    def content_type(self) -> str:
        """
        The content type of the response.
        """
        return self._content_type

    @property
    def headers(self) -> Dict[str, Any]:
        """
        The headers of the response.
        """
        return self._headers

    def add_body(self, data: str) -> None:
        """
        Appends the ``data`` to the body of the response.

        Parameters
        ----------
        data: :class:`str`
            The body to append.
        """
        self._body += data

    def add_header(self, *, key: str, value: str):
        """
        Adds a header to the response.

        Parameters
        ----------
        key: :class:`str`
            The key of the header.
        value: :class:`str`
            The value of the header.
        """
        self._headers[key] = value

    def add_cookie(self, 
                name: str, 
                value: str, 
                *, 
                domain: Optional[str]=None, 
                http_only: bool=False, 
                is_secure: bool=False):
        """
        Adds a cookie to the response.

        Parameters
        ----------
        name: :class:`str`
            The name of the cookie.
        value: :class:`str`
            The value of the cookie.
        domain: Optional[:class:`str`]
            The domain of the cookie.
        http_only: :class:`bool` 
            If the cookie should be set as HTTP only. Defaults to ``False``.
        is_secure: :class:`bool`
            If the cookie should be set as secure. Defaults to ``False``.
        """
        return self.cookies.add_cookie(
            name=name,
            value=value,
            domain=domain,
            http_only=http_only,
            is_secure=is_secure
        )

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'<{name} status={self.status} content_type={self.content_type!r} version={self.version!r}>'

    def encode(self):
        """
        Encodes the response into a sendable bytes object.
        """
        response = [f'HTTP/{self.version} {self.status} {self.status.description}']
        print(self.cookies)

        response.extend(f'{k}: {v}' for k, v in self.headers.items())
        if self.cookies:
            response.append(self.cookies.encode())

        response.append('\r\n')

        response = b'\r\n'.join(part.encode() for part in response)
        if self.body:
            response += self._body.encode()

        return response

class HTMLResponse(Response):
    """
    A class used to build an HTML response
    """
    def __init__(self, 
                body: Optional[str]=None,
                status: Optional[int]=None,
                headers: Optional[Dict[str, Any]]=None,
                version: Optional[str]=None):

        super().__init__(
            body=body, 
            status=status, 
            content_type='text/html', 
            headers=headers, 
            version=version
        )


class JSONResponse(Response):
    """
    A class used to build a JSON response
    """
    def __init__(self, 
                body: Optional[Union[Dict[str, Any], List[Any]]]=None, 
                status: Optional[int]=None, 
                headers: Optional[Dict[str, Any]]=None, 
                version: Optional[str]=None):

        body = body or {}
        super().__init__(
            body=json.dumps(body), 
            status=status, 
            content_type='application/json', 
            headers=headers, 
            version=version
        )

class FileResponse(Response):
    """
    A class used to build a file response

    Parameters
    ----------
    file: :class:`~railway.file.File`
        The file to send.
    status: :class:`int`
        The status code of the response.
    headers: :class:`dict`
        The headers of the response.
    version: :class:`str`
        The HTTP version of the response.
    """
    def __init__(self, 
                file: File,
                status: Optional[int]=None, 
                headers: Optional[Dict[str, str]]=None, 
                version: Optional[str]=None):
        self.file = file

        super().__init__(
            status=status, 
            content_type=self.get_content_type(), 
            headers=headers, 
            version=version
        )

    def get_content_type(self) -> str:
        """
        Gets the content type of the response. 
        You don't have to call this method since it gets called in the constructor.
        """
        filename = self.file.filename
        content_type = None

        if filename:
            content_type, _ = mimetypes.guess_type(filename)

        if not content_type:
            content_type = 'application/octet-stream'

        return content_type

    async def read(self) -> bytes:
        """
        Reads the file, sets the body and returns it as bytes.
        """
        data = await self.file.read()
        self._body = data.decode()

        return data

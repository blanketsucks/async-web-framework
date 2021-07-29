from .objects import Route, WebsocketRoute
from .datastructures import HTTPHeaders, URL, Cookies
from .response import Response
from .utils import find_headers

import yarl
import datetime
import typing
import urllib.parse

if typing.TYPE_CHECKING:
    from .protocol import ApplicationProtocol

__all__ = (
    'Request',
    'RequestDate'
)

class RequestDate:
    def __init__(self, date: typing.Union[datetime.datetime, datetime.timedelta]) -> None:
        self.datatime = date

    def __repr__(self) -> str:
        return self.datatime.__repr__()

    def __add__(self, other: 'RequestDate') -> 'RequestDate':
        if not isinstance(other, RequestDate):
            return RequestDate(self.datatime)

        return RequestDate(self.datatime + other.datatime)

    def __eq__(self, other: 'RequestDate') -> bool:
        if not isinstance(other, RequestDate):
            return NotImplemented

        return self.datatime == other.datatime

    def __sub__(self, other: 'RequestDate') -> 'RequestDate':
        if not isinstance(other, RequestDate):
            return RequestDate(self.datatime)

        return RequestDate(self.datatime - other.datatime)

    def __lt__(self, other: 'RequestDate') -> bool:
        if not isinstance(other, RequestDate):
            return False

        return self.datatime < other.datatime

    def __le__(self, other: 'RequestDate') -> bool:
        if not isinstance(other, RequestDate):
            return False

        return self.datatime <= other.datatime

    def __gt__(self, other: 'RequestDate') -> bool:
        if not isinstance(other, RequestDate):
            return False

        return self.datatime > other.datatime

    def __ge__(self, other: 'RequestDate') -> bool:
        if not isinstance(other, RequestDate):
            return False

        return self.datatime >= other.datatime

    @property
    def year(self):
        return self.datatime.year

    @property
    def month(self):
        return self.datatime.month

    @property
    def day(self):
        return self.datatime.day

    @property
    def hour(self):
        return self.datatime.hour

    @property
    def minute(self):
        return self.datatime.minute

    @property
    def second(self):
        return self.datatime.second


class Request:
    __slots__ = (
        '_encoding', 'version', 'method',
        '_url', 'headers', 'body', 'protocol', 'connection_info',
        '_cookies', 'route'
    )

    def __init__(self,
                method: str,
                url: str,
                headers: typing.Dict,
                protocol: 'ApplicationProtocol',
                version: str,
                body: str):

        self._encoding = "utf-8"

        self.version = version
        self.method = method
        self._url = url
        self.headers = headers
        self._session = None
        self.body = body
        self.protocol = protocol
        self.route: typing.Union[Route, WebsocketRoute] = None

    @property
    def url(self) -> yarl.URL:
        return yarl.URL(self._url)

    @property
    def cookies(self) -> typing.Dict[str, str]:
        cookie = self.headers.get('Cookie', None) or self.headers.get('Set-Cookie')

        if cookie:
            cookies = Cookies(cookie)

            self._cookies = {
                name: cookie.value for name, cookie in cookies.items()
            }
        else:
            self._cookies = {}

        return self._cookies

    @property
    def token(self) -> typing.Optional[str]:
        prefixes = ('Bearer',)
        auth: str = self.headers.get('Authorization', None)

        if auth:
            prefix, token = auth.split(' ', maxsplit=1)
            if prefix not in prefixes:
                return None

            return token

        return None

    @property
    def user_agent(self):
        return self.headers.get('User-Agent')

    @property
    def host(self):
        return self.headers.get('Host')

    @property
    def connection(self):
        return self.headers.get('Connection')

    @property
    def params(self):
        return self.url.query


    def redirect(self, to: str, headers: typing.Dict=None, status: int=None, content_type: str=None):
        headers = headers or {}
        status = status or 302
        content_type = content_type or 'text/plain'

        url = urllib.parse.quote_plus(to, ":/%#?&=@[]!$&'()*+,;")
        headers['Location'] = url

        response = Response(
            status=status,
            content_type=content_type,
            headers=headers
        )

        return response

    @classmethod
    def parse(cls, data: bytes, protocol: 'ApplicationProtocol'):
        headers, body = find_headers(data)
        line, = next(headers)

        parts = line.split(' ')
        headers = dict(headers)

        method = parts[0]
        version = parts[2]
        path = parts[1]

        self = cls(
            method=method,
            url=path,
            version=version,
            protocol=protocol,
            headers=headers,
            body=body,
        )

        return self

    def __repr__(self) -> str:
        return '<Request url={0.url.path!r} method={0.method!r} version={0.version!r} ' \
               'headers={0.headers!r}>'.format(self)

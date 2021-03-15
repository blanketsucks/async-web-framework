from atom.objects import Route, WebsocketRoute
from .datastructures import HTTPHeaders, URL

import datetime
import json
import typing
import humanize
import yarl
from http.cookies import SimpleCookie

if typing.TYPE_CHECKING:
    from .http import ApplicationProtocol

__all__ = (
    'Request',
    'RequestDate'
)


class RequestDate:
    def __init__(self, date: typing.Union[datetime.datetime, datetime.timedelta]) -> None:
        self.datatime = date

        if isinstance(date, datetime.datetime):
            self.humanized = humanize.naturaltime(self.datatime)

        if isinstance(date, datetime.timedelta):
            self.humanized = humanize.naturaldelta(self.datatime)

    def __repr__(self) -> str:
        return self.datatime.__repr__()

    def __add__(self, other: 'RequestDate') -> 'RequestDate':
        if not isinstance(other, RequestDate):
            return RequestDate(self.datatime)

        return RequestDate(self.datatime + other.datatime)

    def __eq__(self, other: 'RequestDate') -> bool:
        if not isinstance(other, RequestDate):
            return False

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
        '_encoding', 'version', 'status_code', 'method',
        'url', 'headers', 'body', 'protocol', 'connection_info',
        '_cookies', 'datetime', 'route'
    )

    def __init__(self,
                 method: str,
                 url: URL,
                 status_code: int,
                 headers: typing.Dict,
                 protocol: 'ApplicationProtocol',
                 date: datetime.datetime,
                 version: str = None,
                 body=None):

        self._encoding = "utf-8"

        self.version = version[:-1]
        self.status_code = status_code
        self.method = method
        self.url = url
        self.headers = HTTPHeaders(headers)
        self.datetime = RequestDate(date)
        self.body = body
        self.protocol = protocol
        self.route: typing.Union[Route, WebsocketRoute] = None

    @property
    def cookies(self):
        cookie = self.headers.get('Cookie', None)

        if cookie:
            cookies = SimpleCookie()
            cookies.load(cookie)

            self._cookies = {
                name: cookie.value for name, cookie in cookies.items()
            }
        else:
            self._cookies = {}

        return self._cookies

    @property
    def token(self):
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

    def __repr__(self) -> str:
        return '<Request url={0.url.raw_path!r} method={0.method!r} status={0.status_code} version={0.version!r} ' \
               'headers={0.headers}>'.format(self)

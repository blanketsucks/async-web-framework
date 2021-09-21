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
import json
from typing import TYPE_CHECKING, Union, Dict, Any, Optional, Tuple, List, Type
import urllib.parse
import datetime

from .response import Response
from .utils import find_headers
from .cookies import CookieJar
from .datastructures import URL
from .sessions import CookieSession
from .responses import Redirection, redirects
from .formdata import FormData
from .server import ClientConnection
from .file import File

if TYPE_CHECKING:
    from .objects import Route, WebsocketRoute
    from .workers import Worker
    from .app import Application

__all__ = (
    'Request',
)

class Request:
    """
    A request that is sent to the server.

    Attributes
    ----------
    method: :class:`str`
        The HTTP method.
    version: :class:`str`
        The HTTP version.
    headers: :class:`dict`
        The HTTP headers.
    created_at: :class:`datetime.datetime`
        The time the request was created.
    route: :class:`~railway.objects.Route`
        The route that the request was sent to.
    worker: 
        The worker that the request was sent to.
    connection: 
        The connection that the request was sent to.
    """
    __slots__ = (
        '_encoding', 'version', 'method', 'worker', 'connection',
        '_url', 'headers', '_body', 'protocol', 'connection_info',
        '_cookies', 'route', '_app', 'peername', 'created_at'
    )

    def __init__(self,
                method: str,
                url: str,
                headers: Dict[str, str],
                version: str,
                body: Union[str, bytes],
                app: Application,
                connection: ClientConnection,
                worker: Worker,
                created_at: datetime.datetime):
        self._encoding = "utf-8"
        self._app = app
        self._url = url
        self._body = body
        self.version: str = version
        self.method: str = method
        self.connection = connection
        self.worker = worker
        self.headers: Dict[str, str] = headers
        self.route: Optional[Union[Route, WebsocketRoute]] = None
        self.created_at: datetime.datetime = created_at

    async def send(self, 
        response: Union[str, bytes, Dict[str, Any], List[Any], Tuple[Any, Any], File, Response, URL, Any],
        *,
        convert: bool=True
    ) -> None:
        """
        Sends a response to the client.

        Parameters
        ----------
        response: 
            The response to send.

        Raises
        ------
        ValueError: If the response is not parsable.
        """
        if convert:
            response = await self.app.parse_response(response)
        else:
            if not isinstance(response, Response):
                raise ValueError('When convert is passed in as False, response must be a Response object')

        await self.worker.write(
            data=response,
            connection=self.connection
        )

        await self.close()

    async def close(self):
        """
        Closes the connection.
        """
        if not self.connection.is_closed():
            await self.connection.close()

    def is_closed(self) -> bool:
        """
        True if the connection is closed.
        """
        return self.connection.is_closed()

    @property
    def app(self) -> 'Application':
        """
        The application.
        """
        return self._app

    @property
    def url(self) -> URL:
        """
        The URL of the request.
        """
        return URL(self._url)

    @property
    def cookies(self) -> Dict[str, str]:
        """
        The cookies of the request.
        """
        jar = self.cookie_jar
        self._cookies = {
            cookie.name: cookie.value for cookie in jar
        }

        return self._cookies

    @property
    def cookie_jar(self) -> CookieJar:
        """
        The cookie jar of the request.
        """
        return CookieJar.from_request(self)

    @property
    def session(self) -> CookieSession:
        """
        The cookie session of the request.
        """
        return CookieSession.from_request(self)

    @property
    def user_agent(self) -> Optional[str]:
        """
        The user agent of the request.
        """
        return self.headers.get('User-Agent')

    @property
    def content_type(self) -> Optional[str]:
        """
        The content type of the request.
        """
        return self.headers.get('Content-Type')

    @property
    def host(self) -> Optional[str]:
        """
        The host of the request.
        """
        return self.headers.get('Host')

    @property
    def query(self) -> Dict[str, str]:
        """
        The query dict of the request.
        """
        return self.url.query

    @property
    def client_ip(self) -> str:
        """
        The IP address of the client.
        """
        return self.connection.peername[0]

    @property
    def server_ip(self) -> str:
        """
        The IP address of the server.
        """
        return self.connection.sockname[0]

    def text(self) -> str:
        """
        The text of the request.
        """
        return self._body.decode() if isinstance(self._body, (bytes, bytearray)) else self._body

    def json(self) -> Dict[str, Any]:
        """
        The JSON body of the request.
        """
        return json.loads(self.text())

    def form(self) -> FormData:
        """
        The form data of the request.
        """
        return FormData.from_request(self)

    def redirect(self, 
                to: Union[str, URL],
                *, 
                body: Any=None, 
                headers: Optional[Dict[str, Any]]=None, 
                status: Optional[int]=None, 
                content_type: Optional[str]=None) -> Response:
        """
        Redirects a request to another URL.

        Parameters
        ----------
        to: Union[str, :class:`~railway.datastructers.URL`]
            The URL to redirect to.
        body: Any
            The body of the response.
        headers: :class:`dict`
            The headers of the response.
        status: :class:`int`
            The status code of the response.
        content_type: :class:`str`
            The content type of the response.
        
        Raises
        ------
        ValueError: If ``status`` is not valid redirection status code.
        """
        headers = headers or {}
        status = status or 302
        content_type = content_type or 'text/plain'

        url = urllib.parse.quote_plus(str(to), ":/%#?&=@[]!$&'()*+,;")
        cls: Optional[Type[Redirection]] = redirects.get(status) # type: ignore

        if not cls:
            ret = f'{status} is not a valid redirect status code'
            raise ValueError(ret)

        response = cls(location=url, body=body, headers=headers, content_type=content_type)
        return response

    @classmethod
    def parse(cls, 
            data: bytes, 
            app: Application, 
            connection: ClientConnection, 
            worker: Worker, 
            created_at: datetime.datetime) -> Request:
        line: str

        hdrs, body = find_headers(data)
        line, = next(hdrs)

        parts = line.split(' ')
        headers: Dict[str, Any] = dict(hdrs) # type: ignore
        
        method = parts[0]
        version = parts[2]
        path = parts[1]

        self = cls(
            method=method,
            url=path,
            version=version,
            headers=headers,
            body=body,
            app=app,
            connection=connection,
            worker=worker,
            created_at=created_at
        )
        
        return self

    def __repr__(self) -> str:
        return '<Request url={0.url.path!r} method={0.method!r} version={0.version!r} ' \
               'headers={0.headers!r}>'.format(self)

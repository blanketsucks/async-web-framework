from __future__ import annotations
import json
from typing import TYPE_CHECKING, Union, Dict, Any, Optional, Tuple, List, Type
import urllib.parse
import datetime

from .objects import Route, WebsocketRoute
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
    from .workers import Worker
    from .app import Application

__all__ = (
    'Request',
)

class Request:
    """
    A request that is sent to the server.

    Attributes:
        method: The HTTP method.
        version: The HTTP version.
        headers: The HTTP headers.
        created_at: The time the request was created.
        route: The [Route](./objects.md) that the request was sent to.
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
        self.headers: Dict[str, Any] = headers
        self.route: Optional[Union[Route, WebsocketRoute]] = None
        self.created_at: datetime.datetime = created_at

    async def send(self, response: Union[str, bytes, Dict[str, Any], List[Any], Tuple[Any, Any], File, Response, Any]) -> None:
        """
        Sends a response to the client.

        Args:
            response: The response to send.
        """
        data = await self.app.parse_response(response)
        await self.worker.write(
            data=data,
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
        Returns:
            True if the connection is closed.
        """
        return self.connection.is_closed()

    @property
    def app(self) -> Application:
        """
        Returns:
            The [Application](./application.md) that the request was sent to.
        """
        return self._app

    @property
    def url(self) -> URL:
        """
        Returns:
            The [URL](./datastructures.md) of the request.
        """
        return URL(self._url)

    @property
    def cookies(self) -> Dict[str, str]:
        """
        Returns:
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
        Returns:
            The [CookieJar](./cookies.md) of the request.
        """
        return CookieJar.from_request(self)

    @property
    def session(self) -> CookieSession:
        """
        Returns:
            The [CookieSession](./cookies.md) of the request.
        """
        return CookieSession.from_request(self)

    @property
    def user_agent(self) -> str:
        """
        Returns:
            The user agent of the request.
        """
        return self.headers.get('User-Agent')

    @property
    def content_type(self) -> str:
        """
        Returns:
            The content type of the request.
        """
        return self.headers.get('Content-Type')

    @property
    def host(self) -> str:
        """
        Returns:
            The host of the request.
        """
        return self.headers.get('Host')

    @property
    def query(self) -> Dict[str, str]:
        """
        Returns:
            The query dict of the request.
        """
        return self.url.query

    @property
    def client_ip(self) -> str:
        """
        Returns:
            The IP address of the client.
        """
        return self.connection.peername[0]

    @property
    def server_ip(self) -> str:
        """
        Returns:
            The IP address of the server.
        """
        return self.connection.sockname[0]

    def text(self) -> str:
        """
        Returns:
            The text of the request.
        """
        return self._body.decode() if isinstance(self._body, (bytes, bytearray)) else self._body

    def json(self) -> Dict[str, Any]:
        """
        Returns:
            The JSON body of the request.
        """
        return json.loads(self.text())

    def form(self) -> FormData:
        """
        Returns:
            The body as a [FormData](./formdata.md) object.
        """
        return FormData.from_request(self)

    def redirect(self, 
                to: str, 
                *, 
                body: Any=None, 
                headers: Optional[Dict[str, Any]]=None, 
                status: Optional[int]=None, 
                content_type: Optional[str]=None) -> Redirection:
        """
        Redirects a request to another URL.

        Args:
            to: The URL to redirect to.
            body: The body of the response.
            headers: The headers of the response.
            status: The status code of the response.
            content_type: The content type of the response.
        
        Returns:
            A response.
        """
        headers = headers or {}
        status = status or 302
        content_type = content_type or 'text/plain'

        url = urllib.parse.quote_plus(to, ":/%#?&=@[]!$&'()*+,;")
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

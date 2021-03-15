
import typing
import asyncio
import ssl
import socket
import functools
import socket
from concurrent.futures import ThreadPoolExecutor

from atom.datastructures import HTTPHeaders, URL
from .reqresp import Request, Response

class _RequestContextManager:
    def __init__(self, req: typing.Coroutine) -> None:
        self.req = req
        
    async def __aenter__(self) -> Response:
        data, self._socket = await self.req
        return data

    async def __aexit__(self, *args, **kwargs):
        self._socket.close()
        return self

class Session:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def __request(self, 
                hostname: str, 
                secure: bool,
                *, 
                body: bytes,
                ssl_context: ssl.SSLContext=...,
                ):
        port = 80
        ip = socket.gethostbyname(hostname)

        ctx = ssl.create_default_context() if ssl_context is ... else ssl_context
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if secure:
            port = 443
            sock = ctx.wrap_socket(sock, server_hostname=hostname)

        sock.connect((ip, port))
        sock.sendall(body)

        frame = self._recv(sock)
        return frame, sock

    def _recv(self, sock: socket.socket):
        data = b''
        sock.settimeout(2)

        while True:
            try:
                buf = sock.recv(1024)
                if not buf or len(buf) < 1 or buf == b'0\r\n\r\n':
                    break
                data += buf
            except socket.timeout:
                break
        
        return data

    async def _request(self, 
                    url: typing.Union[bytes, str, URL], 
                    method: str, 
                    *, 
                    headers: typing.Dict=...,
                    json: typing.Dict=...,
                    ssl: ssl.SSLContext=...) -> typing.Tuple[Response, typing.Union[socket.socket, ssl.SSLSocket]]:

        if isinstance(url, bytes):
            url = url.decode()

        if isinstance(url, str):
            actual = URL(url)
        elif isinstance(url, URL):
            actual = url

        else:
            fmt = 'Expected str or URL but got {0.__class__.__name__} instead'
            raise ValueError(fmt.format(url))

        scheme = actual.scheme
        secure = False

        if scheme == 'https':
            secure = True

        hostname = actual.hostname
        path = actual.path or '/'

        headers = HTTPHeaders({} if headers is ... else headers)
        request = Request(
            url=actual,
            path=path,
            method=method,
            hostname=hostname,
            headers=headers,
            json={} if json is ... else json
        )

        partial = functools.partial(
            self.__request,
            hostname=hostname,
            secure=secure,
            body=request.encode(),
            ssl_context=ssl
        )

        with ThreadPoolExecutor(max_workers=10) as pool:
            data, self._socket = await self.loop.run_in_executor(pool, partial)

        response = Response(data)

        if 300 <= response.status <= 308:
            resp = await self._redirect(request, response)
            return resp

        return response, self._socket

    async def _redirect(self, req: Request, resp: Response):
        location = resp.headers.get('Location')
        if not location:
            return resp

        actual = URL(location)
        response, _ = await self._request(
            url=actual,
            method=req.method,
            headers=req.headers.original
        )

        return response

    def request(self, url: str, method: str, **kwargs):
        return _RequestContextManager(
            req=self._request(url, method, **kwargs),
        )

    def get(self, url: str, **kwargs):
        return self.request(url, 'GET', **kwargs)
    
    def post(self, url: str, **kwargs):
        return self.request(url, 'POST', **kwargs)

    def put(self, url: str, **kwargs):
        return self.request(url, 'PUT', **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request(url, 'DELETE', **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request(url, 'PATCH', **kwargs)

    def options(self, url: str, **kwargs):
        return self.request(url, 'OPTIONS', **kwargs)

class WebsocketSession(Session):

    async def connect(self, uri: str):
        ...
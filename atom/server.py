
from .request import Request
from .response import Response

import socket as sockets
from websockets import handshake, WebSocketCommonProtocol
import asyncio
import typing
from httptools import HttpRequestParser
from httptools.parser import HttpParserUpgrade

if typing.TYPE_CHECKING:
    from .app import Application

__all__ = (
    'WebsocketProtocolConnection',
    'ConnectionInfo',
    'HTTPProtocol',
    'WebsocketProtocol'
)

class WebsocketProtocolConnection(WebSocketCommonProtocol):
    """Just for the name lol"""
    pass

class ConnectionInfo:
    __slots__ = (
        "sockname",
        "peername",
        "server",
        "server_port",
        "client",
        "client_port",
        "ssl",
        "socket"
    )

    def __init__(self, *,
                sockname: typing.Union[str, tuple],
                peername: tuple,
                server: str,
                server_port: int,
                client: str,
                client_port: int,
                ssl: bool,
                socket: sockets.socket):

        self.sockname = sockname
        self.peername = peername
        self.server = server
        self.server_port = server_port
        self.client = client
        self.client_port = client_port
        self.ssl = ssl
        self.socket = socket

class HTTPProtocol(asyncio.Protocol):
    __slots__ = (
        'loop', 'headers', 'request_class', 'parser', 'handler',
        'encoding', 'app', 'status', 'url', 'handler_task',
        'request', 'body', 'transport', 'connection_type', 'host',
        'http_version', 'method', 'path', 'user_agent', 'conn_info'
    )

    def __init__(self, loop: asyncio.AbstractEventLoop, *, app: 'Application') -> None:
        
        self.loop = loop
        self.headers: typing.Dict = {}
        self.request_class = Request
        self.parser = HttpRequestParser(self)
        self.handler = app._handler
        self.encoding: str = 'utf-8'
        self.app = app
        self.status: int = 200

        self.url: str = None
        self.handler_task: asyncio.Task = None
        self.request: Request = None
        self.body = None
        self.transport = None
        self.connection_type = None
        self.http_version = None
        self.method = None
        self.path = None
        self.conn_info = None
        self.user_agent = None

    def on_body(self, body: bytes):
        self.body = body

    def on_header(self, header: bytes, value: bytes):
        header = header.decode(self.encoding)
        self.headers[header] = value.decode(self.encoding)

    def on_status(self, status: bytes):
        status = status.decode(self.encoding)
        self.status = status

    def on_headers_complete(self):
        self.request = self.request_class(
            version=self.http_version,
            method=self.method,
            url=self.path,
            headers=self.headers,
            body=self.body,
            protocol=self,
            status_code=self.status,
            connection_info=self.conn_info,
        )


    def on_message_complete(self):
        self.handler_task = self.loop.create_task(
            self.handler(self.request, self.response_writer)
        )
        self.loop.create_task(
            self.app.dispatch('on_request', self.request)
        )

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.loop.create_task(self.app.dispatch('on_connection_made', transport))
        self.conn_info = self.get_connection_info(transport)

        self.transport = transport

    def connection_lost(self, exc: typing.Optional[Exception]) -> None:
        self.transport = None
        self.loop.create_task(self.app.dispatch('on_connection_lost', exc))

    def response_writer(self, response: Response):
        self.transport.write(str(response).encode(self.encoding))
        self.transport.close()

    def data_received(self, data: bytes) -> None:
        message = data.decode('utf-8')
        strings = message.split('\n')

        self.get_http_info(strings)
        self.parser.feed_data(data)

        self.loop.create_task(self.app.dispatch('on_socket_receive', data))

    def get_http_info(self, data: list):
        method, path, http_version = data[0].split(' ')

        self.method = method
        self.path = path
        self.http_version = http_version
    
    def get_connection_info(self, transport: asyncio.Transport):
        ssl = transport.get_extra_info('sslcontext')
        socket = transport.get_extra_info('socket')
        sockname = transport.get_extra_info('sockname')
        peername = transport.get_extra_info('peername')
        
        server = ''
        server_port = 0
        client = ''
        client_port = 0

        if isinstance(sockname, str):
            server = sockname

        if isinstance(sockname, tuple):
            server = sockname[0]
            server_port = sockname[1]

        if isinstance(peername, tuple):
            client = peername[0]
            client_port = peername[1]

        return ConnectionInfo(
            sockname=sockname,
            peername=peername,
            server=server,
            server_port=server_port,
            client=client,
            client_port=client_port,
            ssl=ssl,
            socket=socket
        )

class WebsocketProtocol(HTTPProtocol):
    def __init__(self,
                timeout: float=20,
                ping_interval: float=20,
                ping_timeout: float=20,
                max_size: int=None,
                max_queue: int=None,
                read_limit: int= 2 ** 16,
                write_limit: int= 2 ** 16,
                *args,
                **kwargs) -> None:

        self.websocket = None
        super().__init__(*args, **kwargs)
        
        self.timeout = timeout
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.max_size = max_size
        self.max_queue = max_queue
        self.read_limit = read_limit
        self.write_limit = write_limit

    def data_received(self, data: bytes) -> None:
        if self.websocket:
            self.websocket.data_received(data)
        else:
            try:
                super().data_received(data)
            except HttpParserUpgrade:
                pass

    def response_writer(self, response: Response):
        if self.websocket:
            return self.transport.close()

        return super().response_writer(response)

    async def _websocket(self, request: Request, subprotocols=None):
        """Literally directly taken from sanic"""
        headers = {}

        key = handshake.check_request(request.headers)
        handshake.build_response(request.headers, key)

        subprotocol = None
        if subprotocols and "Sec-Websocket-Protocol" in request.headers:
            client_subprotocols = [
                p.strip()
                for p in request.headers["Sec-Websocket-Protocol"].split(",")
            ]

            for p in client_subprotocols:
                if p in subprotocols:
                    subprotocol = p
                    headers["Sec-Websocket-Protocol"] = subprotocol
                    break

        rv = b"HTTP/1.1 101 Switching Protocols\r\n"
        for k, v in headers.items():
            rv += k.encode("utf-8") + b": " + v.encode("utf-8") + b"\r\n"
        rv += b"\r\n"

        request.protocol.transport.write(rv)

        self.websocket = WebsocketProtocolConnection(
            close_timeout=self.timeout,
            max_size=self.max_size,
            max_queue=self.max_queue,
            read_limit=self.read_limit,
            write_limit=self.write_limit,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
        )

        self.websocket.is_client = False
        self.websocket.side = "server"

        self.websocket.subprotocol = subprotocol

        self.websocket.connection_made(request.protocol.transport)
        self.websocket.connection_open()
        
        return self.websocket

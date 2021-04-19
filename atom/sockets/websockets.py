from .frame import WebSocketFrame, Data
from .enums import (
    WebSocketCloseCode,
    WebSocketOpcode,
    HTTPStatus,
    WebSocketState
)
from .sockets import socket, Address
from .utils import (
    WSConnectionContextManager,
    WSServerContextManager
)
from .request import Request
from .response import Response
from .protocols import WebsocketProtocol, Protocol
from .transports import WebsocketTransport

import json
import os
import base64
import typing
import hashlib
import asyncio

__all__ = (
    'Websocket',
    'GUID'
)

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class Websocket(socket):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.state = WebSocketState.CLOSED

        self.__port = None
        self.__host = '127.0.0.1'
        self.__path = '/'

        self._handshake_waiter = self.loop.create_future()

    def _set_state(self, state: WebSocketState=...):
        self.state = WebSocketState.CONNECTED if state is ... else state
        return self.state

    async def connect(self, host: str, path: str, port: int, *, do_handshake_on_connect: bool=...):
        addr = await super().connect(host, port)

        self.__port = port
        self.__host = host
        self.__path = path

        if do_handshake_on_connect:
            await self.handshake()

        self._set_state()
        return addr
    
    async def open_connection(self, 
                            protocol: typing.Type[Protocol], 
                            host: str, 
                            port: int, 
                            *, 
                            ssl: bool):

        proto = protocol()
        await super().connect(host, port, ssl=ssl)

        await self._start_protocol(proto)

    def _create_transport(self, protocol, fut):
        transport = WebsocketTransport(
            socket=self,
            protocol=protocol,
            loop=self.loop,
            future=fut
        )

        return transport

    async def open_websocket_connection(self,
                                    protocol: typing.Type[WebsocketProtocol],
                                    host: str,
                                    port: int=...,
                                    path: str=...,
                                    *,
                                    do_handshake_on_connect: bool=...):

        proto = protocol()
        await self.connect(
            host=host,
            port=port,
            path=path,
            do_handshake_on_connect=do_handshake_on_connect
        )

        await self._start_protocol(proto)

    async def _transport_read(self, transport: WebsocketTransport):
        while True:

            data, opcode = await self.receive()
            transport._data_received(data)

            if opcode is WebSocketOpcode.PONG:
                if transport._pong_waiter:
                    transport._pong_waiter.set_result(None)

            transport._clear()

    async def wait_for_handshake_completion(self, timeout: int=...):
        if self._handshake_waiter.done():
            raise RuntimeError(
                'Socket already handshook'
            )

        await asyncio.wait_for(
            self._handshake_waiter,
            timeout=180.0 if timeout is ... else timeout
        )

    async def handshake(self):
        if self._handshake_waiter.done():
            raise RuntimeError(
                'Socket already handshook'
            )

        if self.is_connected:
            port = self.__port
            host = self.__host
            path = self.__path

            self._set_state(WebSocketState.HANDSHAKING)
            await self._client_handshake(
                host=host,
                path=path,
                port=port
            )

            handshake = await self.recv(4096)
            resp = Response.parse(handshake)

            await self._validate_server_handshake(resp)
            self._handshake_waiter.set_result(None)

            return handshake
        
        if self.is_bound:
            handshake = await self.recv(4096)
            request = Request.parse(handshake)

            if 'Sec-Websocket-Version' not in request.headers:
                return handshake

            await self._validate_client_handshake(request)

            self._set_state(WebSocketState.HANDSHAKING)
            await self._server_handshake(request)

            self._handshake_waiter.set_result(None)

            return handshake

        raise RuntimeError(
            'The socket is not connected nor bound'
        )

    async def _client_handshake(self, host: str, path: str, port: int):
        self._check_closed()
        self._check_connected()

        key = base64.b64encode(os.urandom(16))

        headers = {
            'Host': f'{host}:{port}',
            'Connection': 'Upgrade',
            'Upgrade': 'websocket',
            'Sec-WebSocket-Key': key.decode(),
            'Sec-WebSocket-Version': 13
        }

        request = Request(
            method='GET',
            path=path,
            version='1.1',
            headers=headers
        )
        
        await self._write(request)

    async def _write(self, message: typing.Union[Request, Response]):
        print(message.status)
        await self.send(message.encode())

    @staticmethod
    def _parse_ws_key(request: Request) -> str:
        key = request.headers['Sec-WebSocket-Key']

        sha1 = hashlib.sha1((key + GUID).encode()).digest()
        return base64.b64encode(sha1).decode()

    async def _server_handshake(self, request: Request):
        key = self._parse_ws_key(request)

        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Accept': f'{key}'
        }

        resp = Response(
            status=HTTPStatus.SWITCHING_PROTOCOLS,
            headers=headers
        )

        await self._write(resp)

    async def _validate_server_handshake(self, resp: Response):
        ...

    async def _validate_client_handshake(self, request: Request):
        resp = Response(
            status=HTTPStatus.BAD_REQUEST
        )

        if request.method != 'GET':
            resp.status = HTTPStatus.METHOD_NOT_ALLOWED
            await self._write(resp)

            return

        if request.version != 'HTTP/1.1':
            resp.body = 'Invalid HTTP version. Must be atleast 1.1.'
            await self._write(resp)

            return

        required = (
            'Host',
            'Upgrade',
            'Connection',
            'Sec-WebSocket-Version',
            'Sec-WebSocket-Key',
        )

        for header in required:
            if not header in request.headers:
                resp.body = f'Missing {header} header.'
                await self._write(resp)

                return

        for header in required:
            value: str = request.headers[header]

            if header == 'Upgrade':
                if value.lower() != 'websocket':
                    resp.status = HTTPStatus.UPGRADE_REQUIRED
                    await self._write(resp)

                    return

                continue

            if header == 'Sec-WebSocket-Version':
                if value != '13':
                    resp.body = 'Websocket version must be 13.'
                    await self._write(resp)

                    return

                continue

            if header == 'Sec-WebSocket-Key':
                key = base64.b64decode(value)

                if not len(key) == 16:
                    resp.body = 'Websocket key must be of length 16 in bytes.'
                    await self._write(resp)

                    return

                continue

    async def accept(self, timeout: int=..., *, do_handshake_on_connect: bool=...) -> typing.Tuple['Websocket', Address]:
        sock, addr = await super().accept(timeout=timeout)

        if do_handshake_on_connect:
            await sock.handshake()

        sock._set_state(WebSocketState.CONNECTED)
        sock.settimeout(1)

        return sock, addr

    async def send_frame(self, frame: WebSocketFrame):
        self._set_state(WebSocketState.SENDING)

        if self._connected:
            data = frame.encode(masked=True)
        
        if self._bound:
            data = frame.encode()

        await super().send(data)
        self._set_state()

    async def receive(self) -> typing.Tuple[Data, WebSocketOpcode]:
        self._set_state(WebSocketState.READING)
        opcode, raw, frame = await WebSocketFrame.decode(self)

        return Data(raw, frame), opcode
        
    async def receive_bytes(self)-> typing.Tuple[bytes, WebSocketOpcode]:
        data, opcode = await self.receive()
        return data.data, opcode

    async def receive_str(self)-> typing.Tuple[str, WebSocketOpcode]:
        data, opcode = await self.receive()
        return data.as_string(), opcode

    async def receive_json(self)-> typing.Tuple[typing.Dict, WebSocketOpcode]:
        data, opcode = await self.receive()
        return data.as_json(), opcode

    async def send_bytes(self, data: bytes=..., opcode: WebSocketOpcode=...):
        if opcode is ...:
            opcode = WebSocketOpcode.TEXT

        if data is ...:
            data = b''

        frame = WebSocketFrame(opcode=opcode, data=data)
        await self.send_frame(frame)

    async def send_binary(self, data: bytes=...):
        await self.send_bytes(
            data=data,
            opcode=WebSocketOpcode.BINARY
        )

    async def send_str(self, data: str=..., opcode: WebSocketOpcode=...):
        await self.send_bytes(data.encode(), opcode=opcode)

    async def send_json(self, data: typing.Mapping[str, typing.Any]=..., opcode: WebSocketOpcode=...):
        data = json.dumps(data)
        await self.send_str(
            data=data, 
            opcode=opcode
        )

    async def ping(self, data: bytes=...):
        await self.send_bytes(
            data=data, 
            opcode=WebSocketOpcode.PING
        )

    async def pong(self, data: bytes=...):
        await self.send_bytes(
            data=data,
            opcode=WebSocketOpcode.PONG
        )

    async def continuation(self, data: bytes=...):
        await self.send_bytes(
            data=data,
            opcode=WebSocketOpcode.CONTINUATION
        )

    def create_connection(self, host: str, port: int):
        return WSConnectionContextManager(self, self._create_addr(host, port))

    def create_server(self, host: str, port: int, backlog: int=...):
        return WSServerContextManager(self, self._create_addr(host, port), backlog)
    
    async def __aiter__(self):
        self._check_closed()
        self._check_connected()

        while True:
            try:
                data = await self.receive()
                if not data:
                    break
                
                yield data
            except:
                break

    def _close(self):
        return super().close()
    
    async def close(self, *, code: WebSocketCloseCode=..., data: bytes=...):
        if code is ...:
            code = WebSocketCloseCode.NORMAL

        if data is ...:
            data = b''

        code = code.to_bytes(2, 'big', signed=False)
        data = code + data

        frame = WebSocketFrame(opcode=WebSocketOpcode.CLOSE, data=data)

        await self.send_frame(frame)
        self._set_state(WebSocketState.CLOSED)

        return self._close()

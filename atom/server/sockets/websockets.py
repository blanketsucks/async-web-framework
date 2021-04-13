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

import json
import os
import base64
import typing
import hashlib
import asyncio

__all__ = (
    'Websocket',
)

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class Websocket(socket):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.state = WebSocketState.CLOSED

        self.__port = None
        self.__host = '127.0.0.1'
        self.__path = '/'

        self._handshake_waiter = self._loop.create_future()

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
        self.settimeout(1)

        return addr

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
        self.settimeout(10)

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

            handshake = await self.recv()
            await self._validate_server_handshake(handshake)

            self._handshake_waiter.set_result(None)
            return
        
        if self.is_bound:
            handshake = await self.recv(4096)
            await self._validate_client_handshake(handshake)

            self._set_state(WebSocketState.HANDSHAKING)
            await self._server_handshake(handshake)

            self._handshake_waiter.set_result(None)
            return

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

        await self._write(opening_header=f'GET {path} HTTP/1.1', headers=headers)

    async def _write(self, 
                    status: HTTPStatus=...,
                    data: str=... ,
                    *,
                    content_type: str=...,
                    opening_header: str=..., 
                    headers: typing.Mapping[str, typing.Any]=...):
        if status is ...:
            status = HTTPStatus.OK

        if opening_header is ...:
            opening_header = f'HTTP/1.1 {status.value} {status.description}'

        if headers is ...:
            headers = {}

        if data is ...:
            data = ''

        if content_type is ...:
            content_type = 'text/plain'

        messages = [opening_header]

        if data:
            messages.append(f'Content-Type: {content_type}')
            messages.append(f'Content-Length: {len(data)}')

        messages.extend([f'{k}: {v}' for k, v in headers.items()])

        message = '\r\n'.join(messages)
        message += '\r\n\r\n'

        if data:
            message += data

        await super().send(message.encode())

    def _parse_ws_key(self, data: bytes) -> str:
        key = ''

        for header in data.decode().split('\r\n'):
            data: typing.List[str] = header.split(': ', maxsplit=1)

            if not len(data) == 2:
                continue
            
            item, value = data
            if item == 'Sec-WebSocket-Key':
                key = value
                break

        sha1 = hashlib.sha1((key + GUID).encode()).digest()
        return base64.b64encode(sha1).decode()

    async def _server_handshake(self, data: bytes):
        self.settimeout(0.5)
        key = self._parse_ws_key(data)

        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Accept': f'{key}'
        }

        messages = [
            'HTTP/1.1 101 Switching Protocols'
        ]
        messages.extend([f'{k}: {v}' for k, v in headers.items()])

        handshake = '\r\n'.join(messages)
        handshake += '\r\n\r\n'

        await super().send(handshake.encode())

    async def _validate_server_handshake(self, data: bytes):
        ...

    async def _validate_client_handshake(self, data: bytes):
        encoded = data.decode()
        headers = encoded.split('\r\n')

        method, path, version = headers.pop(0).split(' ')

        if method != 'GET':
            return await self._write(HTTPStatus.METHOD_NOT_ALLOWED)

        if version != 'HTTP/1.1':
            return await self._write(
                status=HTTPStatus.BAD_REQUEST,
                data='Invalid HTTP version. Must be atleast 1.1.'
            )

        all_headers = []
        for header in headers:
            if not header:
                continue

            item, value = header.split(': ')
            all_headers.append(item)

            if item == 'Upgrade':
                if value.lower() != 'websocket':
                    return await self._write(
                        status=HTTPStatus.UPGRADE_REQUIRED
                    )

                continue

            if item == 'Sec-WebSocket-Version':
                if value != '13':
                    return await self._write(
                        status=HTTPStatus.BAD_REQUEST,
                        data='Websocket version must be 13.'
                    )

                continue

            if item == 'Sec-WebSocket-Key':
                key = base64.b64decode(value)

                if not len(key) == 16:
                    return await self._write(
                        status=HTTPStatus.BAD_REQUEST,
                        data='Websocket key must be of length 16 in bytes.'
                    )

                continue

        if 'Host' not in all_headers:
            return await self._write(
                status=HTTPStatus.BAD_REQUEST,
                data='Missing Host header.'
            )

        if 'Connection' not in all_headers:
            return await self._write(
                status=HTTPStatus.BAD_REQUEST,
                data='Missing Connection header.'
            )

    async def accept(self, timeout: int=..., *, do_handshake_on_connect: bool=...) -> typing.Tuple['Websocket', Address]:
        sock, addr = await super().accept(timeout=timeout)

        if do_handshake_on_connect:
            await sock.handshake()

        sock._set_state(WebSocketState.CONNECTED)
        sock.settimeout(1)

        return sock, addr

    async def send(self, frame: WebSocketFrame):
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
        
    async def receive_bytes(self):
        data, = await self.receive()
        return data.data

    async def receive_str(self):
        data, = await self.receive()
        return data.as_string()

    async def receive_json(self):
        data, = await self.receive()
        return data.as_json()

    async def send_bytes(self, data: bytes=..., opcode: WebSocketOpcode=...):
        if opcode is ...:
            opcode = WebSocketOpcode.TEXT

        if data is ...:
            data = b''

        frame = WebSocketFrame(opcode=opcode, data=data)
        await self.send(frame)

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

        await self.send(frame)
        self._set_state(WebSocketState.CLOSED)

        return self._close()


import asyncio
import typing
import socket

from .enums import WebSocketOpcode
from .frame import Data

if typing.TYPE_CHECKING:
    from . import protocols
    from atom import sockets

class TransportClosed(Exception):
    ...

class BaseTransport:
    def __init__(self, protocol, sock, loop) -> None:
        self._protocol = protocol
        self._socket = sock
        self._loop = loop

        self._closed = False
        self._dispatch('connection_made', self)

    @property
    def protocol(self):
        return self._protocol

    def is_closed(self):
        return self._closed

    def _dispatch(self, name, *args):
        method = getattr(self._protocol, 'on_' + name)
        self._loop.create_task(
            coro=method(*args)
        )

    def close(self):
        if self._closed:
            raise TransportClosed('Transport is already closed')

        self._dispatch('connection_lost')

        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()

class ReadTransport(BaseTransport):
    def __init__(self, protocol, sock, loop) -> None:
        super().__init__(protocol, sock, loop)

        self._paused_reading = False
        self._read_future = None

        self._data = bytearray(65536)
        self._loop.call_soon(self._reading_loop)

    def is_reading(self):
        return not self._closed and not self._paused_reading

    def pause_reading(self):
        if self._closed or self._paused_reading:
            return
        
        self._paused_reading = True

    def resume_reading(self):
        if self._closed or not self._paused_reading:
            return

        self._paused_reading = False

    def _reading_loop(self, future=None):
        length = -1
        data = None
        
        if future:
            self._read_future = None
            if future.done():
                length = future.result()

                if length == 0:
                    return

                data = self._data[:length]
                data = bytes(data)
            else:
                future.cancel()

        if not self._paused_reading:
            sock = self._sock._socket
            self._read_future = self._sock._run_socket_operation(sock.recv_into, self._data)
            self._read_future.add_done_callback(self._loop_reading)
            
        if length > -1:
            self._dispatch('data_receive', data)

    def close(self):
        super().close()

        if self._read_future:
            self._read_future.cancel()
            self._read_future = None

class WriteTransport(BaseTransport):
    def __init__(self, protocol, sock, loop) -> None:
        super().__init__(protocol, sock, loop)

        self._paused_writing = False

    def is_writing(self):
        return not self._closed and not self._paused_writing

    async def write(self, data):
        if self._closed or self._paused_writing:
            return

        await self._sock.send(data)

    async def writelines(self, data):
        data = b''.join(data)
        await self.write(data)

    def pause_writing(self):
        if self._closed or self._paused_writing:
            return

        self._paused_writing = True

    def resume_writing(self):
        if self._closed or not self._paused_writing:
            return

        self._paused_writing = False

class Transport(WriteTransport, ReadTransport):
    ...

class WebsocketTransport:
    ...

# class WebsocketTransport(Transport):
#     def __init__(self, 
#                 socket: 'sockets.Websocket', 
#                 protocol: 'protocols.Protocol', 
#                 *, 
#                 loop: asyncio.AbstractEventLoop, 
#                 futureure: asyncio.futureure) -> None:

#         super().__init__(socket=socket, protocol=protocol, loop=loop, futureure=futureure)
#         self._sock = socket

#     def write(self, data: bytes=..., *, opcode: WebSocketOpcode=...) -> typing.Optional[asyncio.futureure[int]]:
#         if self._paused_writing:
#             return

#         futureure = self._wrap_writer(self._sock.send_bytes, data, opcode)
#         self._set()

#         return futureure

#     def send(self, data: bytes):
#         if self._paused_writing:
#             return

#         futureure = super().write(data)
#         return futureure

#     async def ping(self, data: bytes=...):
#         await self.write(data, opcode=WebSocketOpcode.PING)

#     def _data_received(self, data: Data):
#         if self._closed:
#             return

#         if self._paused_reading:
#             if isinstance(self._pause_buffer, bytearray):
#                 self._pause_buffer += data.data
#                 return

#             return 

#         self._dispatch('data_receive', data)

#     def _cleanup(self):        
#         self._sock.shutdown(socket.SHUT_RDWR)
#         self._sock._close()

#         self._dispatch('connection_lost')

#         if self._conn_futureure:
#             self._conn_futureure.set_result(None)

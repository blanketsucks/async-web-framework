
import asyncio
import typing
import warnings
import socket

from .enums import WebSocketOpcode
from .frame import Data

if typing.TYPE_CHECKING:
    from . import protocols
    from . import sockets

Writer = typing.Callable[[bytes], typing.Coroutine[None, None, typing.Any]]
WebsocketWriter = typing.Callable[[bytes, WebSocketOpcode], typing.Coroutine[None, None, typing.Any]]

class TransportClosed(Exception):
    ...

class Transport:
    def __init__(self, 
                socket: 'sockets.socket', 
                protocol: 'protocols.Protocol',
                *, 
                loop: asyncio.AbstractEventLoop,
                future: asyncio.Future=None) -> None:

        self._sock = socket
        self._protocol = protocol
        self._loop = loop
        self._extras = {}

        print(self._protocol)

        self._conn_future = future

        self._closed = False

        self._paused_reading = False
        self._paused_writing = False

        self._writers: typing.List[asyncio.Future] = []
        self._pause_buffer = None

        self.__read_event = asyncio.Event()
        self._dispatch('connection_made', self)

        self._extras['socket'] = self._sock

        self._extras['laddr'] = self._sock._laddr
        self._extras['raddr'] = self._sock._raddr

    def get_extra(self, name: str):
        return self._extras.get(name)

    @property
    def is_closed(self):
        return self._closed

    @property
    def protocol(self):
        return self._protocol

    def is_reading(self):
        return not self._closed and not self._paused_reading

    def is_writing(self):
        return not self._closed and not self._paused_writing

    def get_buffer(self) -> bytearray:
        if not self._pause_buffer:
            return bytearray()

        data = self._pause_buffer
        self._pause_buffer.clear()

        return data

    def _ensure_writers(self):
        for writer in self._writers:
            if writer.done():
                self._writers.remove(writer)

    def _wrap_writer(self, method: typing.Union[Writer, WebsocketWriter], *args) -> asyncio.Future:
        self._ensure_writers()
        future = asyncio.ensure_future(method(*args))

        self._writers.append(future)
        return future

    def write(self, data: bytes) -> typing.Optional[asyncio.Future[int]]:
        if self._paused_writing:
            return

        future = self._wrap_writer(self._sock.send, data)

        self.__read_event.set()
        return future

    def writelines(self, data: typing.Iterable[bytes], *, sep: str='\n'):
        data = [item.decode() for item in data]

        actual = f'{sep}'.join(data)
        return self.write(actual.encode())

    def pause_writing(self):
        if self._closed or self._paused_writing:
            return

        for future in self._writers:
            future.cancel()

        self._paused_writing = True

    def resume_writing(self):
        if self._closed or not self._paused_writing:
            return

        self._paused_writing = False

    def pause_reading(self, feed_into_buffer: bool=...):
        if self._closed or self._paused_reading:
            return

        if feed_into_buffer:
            self._pause_buffer = bytearray()
        
        self._paused = True

    def resume_reading(self):
        if self._closed or not self._paused_reading:
            return

        if self._pause_buffer:
            self._pause_buffer.clear()

        self._paused = False

    async def _wait(self):
        await self.__read_event.wait()

    def _clear(self):
        self.__read_event.clear()

    def _set(self):
        self.__read_event.set()

    def _data_received(self, data: bytes):
        if self._closed:
            return

        if self._paused_reading:
            if isinstance(self._pause_buffer, bytearray):
                self._pause_buffer += data
                return

            return 

        self._dispatch('data_receive', data)

    def _dispatch(self, name: str, *args):
        method = getattr(self._protocol, 'on_' + name)
        return self._loop.create_task(method(*args))

    async def _call(self, name: str, *args):
        method = getattr(self._protocol, 'on_' + name)
        await method(*args)

    def _cleanup(self):
        self._sock.shutdown(socket.SHUT_RDWR)
        self._sock.close()

        if self._conn_future:
            self._conn_future.set_result(None)

    def close(self):
        if self._closed:
            raise TransportClosed(
                'Transport is already closed'
            )
        for writer in self._writers:
            writer.cancel()

        self._dispatch('connection_lost')
        self._closed = True

        self._cleanup()


class WebsocketTransport(Transport):
    def __init__(self, 
                socket: 'sockets.Websocket', 
                protocol: 'protocols.Protocol', 
                *, 
                loop: asyncio.AbstractEventLoop, 
                future: asyncio.Future) -> None:

        super().__init__(socket=socket, protocol=protocol, loop=loop, future=future)
        self._sock = socket

        self._pong_waiter = None

    def write(self, data: bytes=..., *, opcode: WebSocketOpcode=...) -> typing.Optional[asyncio.Future[int]]:
        if self._paused_writing:
            return

        future = self._wrap_writer(self._sock.send_bytes, data, opcode)
        self._set()

        return future

    def send(self, data: bytes):
        if self._paused_writing:
            return

        future = super().write(data)
        return future

    async def ping(self, data: bytes=...):
        await self.write(data, opcode=WebSocketOpcode.PING)
        self._pong_waiter = fut = self._loop.create_future()

        return fut

    def _data_received(self, data: Data):
        if self._closed:
            return

        if self._paused_reading:
            if isinstance(self._pause_buffer, bytearray):
                self._pause_buffer += data.data
                return

            return 

        self._dispatch('data_receive', data)

    def _cleanup(self):        
        self._sock.shutdown(socket.SHUT_RDWR)
        self._sock._close()

        if self._conn_future:
            self._conn_future.set_result(None)

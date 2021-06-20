import asyncio
import ssl
import socket
from typing import Tuple
import time
import typing
from concurrent.futures import ThreadPoolExecutor
from atom import sockets
import functools

import ssl

_T = typing.TypeVar('_T')

class _dummy:
    def __init__(self, sock: socket.socket) -> None:
        self.socket = sock

        self.context = ssl.create_default_context()

        self.type = sock.type
        self.family = sock.family
        self.proto = sock.proto

    def fileno(self):
        return self.socket.fileno()

    def accept(self):
        return self.socket.accept()

    def connect(self, addr):
        if addr[1] == 443:
            self.socket = self.context.wrap_socket(self.socket, server_hostname=addr[0])

        return self.socket.connect(addr)

    def send(self, buffer):
        return self.socket.send(buffer)

    def recv(self, nbytes):
        return self.socket.recv(nbytes)

    def recv_into(self, buffer, nbytes):
        return self.socket.recv_into(buffer, nbytes)

    def getsockopt(self, level, opt):
        return self.socket.getsockopt(level, opt)

    def getsockname(self):
        return self.socket.getsockname()

    def getpeername(self):
        return self.socket.getpeername()

    def gettimeout(self):
        return self.socket.gettimeout()

    def close(self):
        return self.socket.close()

    def shutdown(self, how):
        return self.socket.shutdown(how)

class Socket:
    def __init__(self) -> None:
        self._socket = None
        self._socket = self._create_new_socket()

        self._loop = asyncio.get_event_loop()
        self._executor = ThreadPoolExecutor()

    async def _to_thread(self, func, *args, **kwargs):
        partial = functools.partial(func, *args, **kwargs)
        return await self._loop.run_in_executor(
            self._executor, partial
        )

    def _wrap(self, 
            callback: typing.Callable[..., _T],
            *args: typing.Tuple[typing.Any, ...], 
            **kwargs: typing.Mapping[str, typing.Any]) -> 'asyncio.Future[_T]':

        async def wrapper(callback):
            func = getattr(self._loop, 'sock_' + callback.__name__, None)

            if func:
                try:
                    result = await func(self._socket, *args, **kwargs)
                    return result
                except OSError:
                    pass
            
            result = await self._to_thread(callback, *args, **kwargs)
            return result

        return asyncio.ensure_future(wrapper(callback))

    def _create_new_socket(self):
        if self._socket:
            self._socket.close()
            self._socket = None

        self._socket = sock = _dummy(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        return sock

    def connect(self, address: Tuple[str, int]):
        future = self._wrap(self._socket.connect, address)
        return future

    def send(self, data):
        future = self._wrap(self._socket.send, data)
        return future

    async def recv(self, nbytes):
        return await self._wrap(self._socket.recv, nbytes)

    def _close(self):
        self._socket.close()

async def timeit(func, args, times):
    start = time.time()
    av = []

    for _ in range(times):
        begin = time.time()
        await func(*args)
        end_of_iter = time.time()

        av.append(end_of_iter - begin)

    end = time.time()
    print(f'{func.__name__} took {end - start} for {times} iterations.')

aaa = ('google.com', 443)
req = b'GET / HTTP/1.1\r\nHost: google.com\r\n\r\n'

async def a():
    sock = Socket()
    await sock.connect(aaa)
    await sock.send(req)

    recv = await sock.recv(4096)
    print(recv)
    sock._close()

async def i():
    sock = sockets.socket()
    await sock.connect(*aaa)
    await sock.send(req)

    recv = await sock.recv(4096)
    print(recv)
    sock.close()

async def main():
    loop = asyncio.get_event_loop()

    await timeit(a, (), 1)
    await timeit(i, (), 1)

asyncio.run(main())
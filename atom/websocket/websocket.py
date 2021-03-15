
import socket
import asyncio
import concurrent.futures

from .frame import WebsocketFrame

MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

__all__ = (
    'MAGIC',
    'Websocket'
)


class Websocket:
    def __init__(self, __socket: socket.socket, __loop: asyncio.AbstractEventLoop) -> None:

        self.__pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self.__socket = __socket
        self.__loop = __loop
        self._frame = WebsocketFrame()

    def this_sucks(self):
        ...

    def close(self):
        self.__socket.close()

from .bases import Protocol
from .connection import HTTPConnection

import typing
import asyncio

def parse_request_info(cls: 'HTTPProtocol', data: typing.List):
    request_info: str = data[0]

    cls.method = request_info.split(' ')[0]
    cls.path = request_info.split(' ')[1]
    cls.http = request_info.split(' ')[2]

    data.remove(request_info)

class HTTPProtocol(Protocol):
    def __init__(self, loop: typing.Optional[asyncio.AbstractEventLoop]) -> None:
        self.loop = loop

        self.method: str = None
        self.path: str = None
        self.http: str = None

    async def on_connection_made(self, connection: HTTPConnection):
        ...

    async def on_request(self):
        ...

    def parse_data(self, data: bytes):
        decoded = data.decode('utf-8')
        infos = decoded.split('\r\n')

        parse_request_info(self, infos)
        self.http_info: typing.Dict[str, str] = {}

        for info in infos:
            if len(info) == 0:
                continue

            items = info.split(': ')
            self.http_info[items[0]] = items[1]

    def __repr__(self) -> str:
        return '<HTTPProtcol>'


import asyncio
import socket
import enum
import typing

class OPCode(enum.Enum):
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


class WebsocketFrame:
    def this_sucks(self):
        ...
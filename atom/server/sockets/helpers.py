import typing

from .sockets import socket, HTTPSocket
from .websockets import Websocket

__all__ = (
    'create_connection',
    'create_server',
    'create_http_connection',
    'create_http_server',
    'create_websocket_connection',
    'create_websocket_server',
    'gethostbyaddr',
    'gethostbyname',
    'getaddrinfo',
    'getprotobyname',
    'getservbyport',
    'getservbyname',
    'if_nameindex',
    'if_nametoindex',
    'if_indextoname'
)

def create_connection(host: str, port: int, *, ssl: bool=False, **kwargs):
    sock = socket(**kwargs)
    return sock.create_connection(host, port)

def create_server(host: str, port: int, backlog: int=..., **kwargs):
    sock = socket(**kwargs)
    return sock.create_server(host, port, backlog)

def create_http_connection(host: str, port: int, *, ssl: bool=False, **kwargs):
    sock = HTTPSocket(**kwargs)
    return sock.create_connection(host, port)

def create_http_server(host: str, port: int, backlog: int=..., **kwargs):
    sock = HTTPSocket(**kwargs)
    return sock.create_server(host, port, backlog)

def create_websocket_connection(host: str, port: int, **kwargs):
    sock = Websocket(**kwargs)
    return sock.create_connection(host, port)

def create_websocket_server(host: str, port: int, backlog: int=..., **kwargs):
    sock = Websocket(**kwargs)
    return sock.create_server(host, port, backlog)

async def gethostbyaddr(address: str) -> typing.Tuple[str, typing.List[str], typing.List[str]]:
    sock = socket()
    host = await sock.gethostbyaddr(address)

    sock.close()
    return host

async def gethostbyname(name: str) -> str:
    sock = socket()
    host = await sock.gethostbyname(name)

    sock.close()
    return host

async def getaddrinfo(host: str, port: int):
    sock = socket()
    addr = await sock.getaddrinfo(host, port)

    sock.close()
    return addr

async def getprotobyname(name: str) -> int:
    sock = socket()
    proto = await sock.getprotobyname(name)

    sock.close()
    return proto

async def getservbyname(service: str, protocol: str) -> int:
    sock = socket()
    serv = await sock.getservbyname(service, protocol)

    sock.close()
    return serv

async def getservbyport(port: int, protocol: str) -> str:
    sock = socket()
    serv = await sock.getservbyport(port, protocol)

    sock.close()
    return serv

async def if_nameindex() -> typing.List[typing.Tuple[str, int]]:
    sock = socket()
    nameindex = await sock.if_nameindex()

    sock.close()
    return nameindex

async def if_nametoindex(name: str) -> int:
    sock = socket()
    index = await sock.if_nametoindex(name)

    sock.close()
    return index

async def if_indextoname(index: int) -> str:
    sock = socket()
    index = await sock.if_indextoname(index)

    sock.close()
    return index
from typing import Any, Callable, Coroutine, Iterator, Optional, TYPE_CHECKING, Tuple, Union
import asyncio
import pathlib
from asyncio.trsock import TransportSocket

from .websockets import Websocket

if TYPE_CHECKING:
    from .settings import Settings
    from .objects import Listener, Route as _Route, WebsocketRoute as _WebsocketRoute
    from .request import Request
    
__all__ = (
    'AbstractRouter',
    'AbstractApplication',
    'AbstractProtocol',
)

Route = Callable[[Callable[['Request'], Coroutine[Any, Any, Any]]], '_Route']
WebsocketRoute = Callable[[Callable[['Request'], Coroutine[Any, Any, Any]]], '_WebsocketRoute']
Middleware = Callable[['Request', Callable[['Request'], Coroutine[Any, Any, Any]]], Coroutine[Any, Any, Any]]

class AbstractConnection:
    @property
    def socket(self) -> TransportSocket:
        raise NotImplementedError

    @property
    def peername(self) -> Tuple[str, int]:
        raise NotImplementedError

    @property
    def sockname(self) -> Tuple[str, int]:
        raise NotImplementedError

    def is_closed(self) -> bool:
        raise NotImplementedError

    def get_protocol(self) -> 'AbstractProtocol':
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def write(self, data: bytes) -> None:
        raise NotImplementedError

class AbstractRouter:
    def add_route(self, route: Union['_Route', '_WebsocketRoute']) -> Union['_Route', '_WebsocketRoute']:
        raise NotImplementedError

    def remove_route(self, route: Union['_Route', '_WebsocketRoute']) -> Union['_Route', '_WebsocketRoute']:
        raise NotImplementedError

    def websocket(self, path: str) -> WebsocketRoute:
        raise NotImplementedError

    def route(self, path: str, method: str) -> Route:
        raise NotImplementedError

    def get(self, path: str) -> Route:
        raise NotImplementedError

    def post(self, path: str) -> Route:
        raise NotImplementedError

    def put(self, path: str) -> Route:
        raise NotImplementedError

    def patch(self, path: str) -> Route:
        raise NotImplementedError

    def delete(self, path: str) -> Route:
        raise NotImplementedError

    def options(self, path: str) -> Route:
        raise NotImplementedError

    def head(self, path: str) -> Route:
        raise NotImplementedError

    def middleware(self, func: Middleware) -> Middleware:
        raise NotImplementedError

    def __iter__(self) -> Iterator[Union['_Route', '_WebsocketRoute']]:
        raise NotImplementedError

class AbstractApplication:
    loop: Optional[asyncio.AbstractEventLoop]
    settings: 'Settings'
    url_prefix: str
    surpress_warnings: bool

    def __init__(self, 
                url_prefix: str=None, 
                *, 
                settings_file: Union[str, pathlib.Path]=None, 
                load_settings_from_env: bool=None,
                supress_warnings: bool=False) -> None:
        ...

    def is_closed(self) -> bool:
        raise NotImplementedError

    async def start(self, host: str=None, port: int=None) -> None:
        raise NotImplementedError

    async def wait_closed(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def add_route(self, route: Union['_Route', '_WebsocketRoute']) -> Union['_Route', '_WebsocketRoute']:
        raise NotImplementedError

    def get_route(self, method: str, path: str) -> Union['_Route', '_WebsocketRoute']:
        raise NotImplementedError

    def remove_route(self, route: Union['_Route', '_WebsocketRoute']) -> Union['_Route', '_WebsocketRoute']:
        raise NotImplementedError

    def add_router(self, router: AbstractRouter) -> AbstractRouter:
        raise NotImplementedError

    def websocket(self, path: str) -> WebsocketRoute:
        raise NotImplementedError

    def route(self, path: str, method: str) -> Route:
        raise NotImplementedError

    def get(self, path: str) -> Route:
        raise NotImplementedError

    def post(self, path: str) -> Route:
        raise NotImplementedError

    def put(self, path: str) -> Route:
        raise NotImplementedError

    def patch(self, path: str) -> Route:
        raise NotImplementedError

    def delete(self, path: str) -> Route:
        raise NotImplementedError

    def options(self, path: str) -> Route:
        raise NotImplementedError

    def head(self, path: str) -> Route:
        raise NotImplementedError

    def add_event_listener(self, coro: Callable[..., Coroutine], name: str=None) -> Listener:
        raise NotImplementedError

    def remove_event_listener(self, func: Callable[..., Coroutine]=None, name: str=None) -> None:
        raise NotImplementedError

    def event(self, name: str=None) -> Callable[[Callable[..., Coroutine]], Listener]:
        raise NotImplementedError
    

class AbstractProtocol(asyncio.Protocol):
    def is_websocket_request(self, request: Request):
        raise NotImplementedError

    def parse_websocket_key(self, request: Request):
        raise NotImplementedError

    def handshake(self, request: Request):
        raise NotImplementedError

    def handle_request(self, request, websocket):
        raise NotImplementedError

    def connection_made(self, transport: asyncio.Transport) -> None:
        raise NotImplementedError

    def connection_lost(self, exc: Optional[Exception]) -> None:
        raise NotImplementedError

    def store_websocket(self, ws: Websocket):
        raise NotImplementedError

    def get_websocket(self):
        raise NotImplementedError

    def feed_into_websocket(self, data: bytes):
        raise NotImplementedError

    def ensure_websockets(self):
        raise NotImplementedError

    def data_received(self, data: bytes) -> None:
        raise NotImplementedError
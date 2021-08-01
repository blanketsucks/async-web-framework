from typing import Any, Callable, Coroutine, Optional, Union
import asyncio
import pathlib

from .settings import Settings
from .request import Request
from .websockets import Websocket
from .objects import Route as _Route, WebsocketRoute as _WebsocketRoute

__all__ = (
    'AbstractRouter',
    'AbstractApplication',
    'AbstractProtocol',
)

Route = Callable[[Callable[[Request], Coroutine[Any, Any, Any]]], _Route]
WebsocketRoute = Callable[[Callable[[Request], Coroutine[Any, Any, Any]]], _WebsocketRoute]
Middleware = Callable[[Request, Callable[[Request], Coroutine[Any, Any, Any]]], Coroutine[Any, Any, Any]]

class AbstractRouter:
    def add_route(self, route: Union[_Route, _WebsocketRoute]) -> Union[_Route, _WebsocketRoute]:
        raise NotImplementedError

    def remove_route(self, route: Union[_Route, _WebsocketRoute]) -> Union[_Route, _WebsocketRoute]:
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

class AbstractApplication:
    loop: asyncio.AbstractEventLoop
    settings: Settings
    url_prefix: str
    surpress_warnings: bool

    def __init__(self, 
                url_prefix: str=None, 
                *, 
                loop: asyncio.AbstractEventLoop=None,
                settings_file: Union[str, pathlib.Path]=None, 
                load_settings_from_env: bool=None,
                supress_warnings: bool=False) -> None:
        ...

    def is_closed(self) -> bool:
        raise NotImplementedError

    def get_transport(self) -> Optional[asyncio.Transport]:
        raise NotImplementedError

    def get_request_task(self) -> Optional[asyncio.Task]:
        raise NotImplementedError
    
    async def start(self, host: str=None, port: int=None) -> None:
        raise NotImplementedError

    async def wait_closed(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def run(self, *args, **kwargs) -> None:
        raise NotImplementedError

    def add_route(self, route: Union[_Route, _WebsocketRoute]) -> Union[_Route, _WebsocketRoute]:
        raise NotImplementedError

    def add_router(self, router: AbstractRouter) -> AbstractRouter:
        raise NotImplementedError

    def websocket(self, path: str) -> WebsocketRoute:
        raise NotImplementedError

    def route(self, path: str, method: str) -> Route:
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
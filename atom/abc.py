from __future__ import annotations
from typing import Any, Callable, Coroutine, Iterator, Optional, TYPE_CHECKING, Union
import asyncio
import pathlib

from .server import ClientConnection
from .response import Response

if TYPE_CHECKING:
    from .settings import Settings
    from .objects import Listener, Route as _Route, WebsocketRoute as _WebsocketRoute
    from .request import Request
    
    
__all__ = (
    'AbstractRouter',
    'AbstractApplication',
)

# Route = Callable[[Callable[[Request], Coroutine[Any, Any, Any]]], _Route]
# WebsocketRoute = Callable[[Callable[[Request], Coroutine[Any, Any, Any]]], _WebsocketRoute]
# Middleware = Callable[[Request, Callable[[Request], Coroutine[Any, Any, Any]]], Coroutine[Any, Any, Any]]

Route = Callable
WebsocketRoute = Callable
Middleware = Callable


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

    def __iter__(self) -> Iterator[Union[_Route, _WebsocketRoute]]:
        raise NotImplementedError

class AbstractApplication:
    loop: Optional[asyncio.AbstractEventLoop]
    settings: Settings
    url_prefix: str
    surpress_warnings: bool

    def __init__(self,
                host: str=None,
                port: int=None, 
                url_prefix: str=None, 
                *, 
                settings_file: Union[str, pathlib.Path]=None, 
                load_settings_from_env: bool=None,
                supress_warnings: bool=False) -> None:
        ...

    def is_closed(self) -> bool:
        raise NotImplementedError

    async def start(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    def add_route(self, route: Union[_Route, _WebsocketRoute]) -> Union[_Route, _WebsocketRoute]:
        raise NotImplementedError

    def get_route(self, method: str, path: str) -> Union[_Route, _WebsocketRoute]:
        raise NotImplementedError

    def remove_route(self, route: Union[_Route, _WebsocketRoute]) -> Union[_Route, _WebsocketRoute]:
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
    

class AbstractWorker:
    id: int

    async def start(self, loop: asyncio.AbstractEventLoop):
        raise NotImplementedError

    async def run(self, loop: asyncio.AbstractEventLoop):
        raise NotImplementedError

    async def write(self, data: Union[Response, Request], connection: ClientConnection) -> int:
        raise NotImplementedError

    async def stop(self):
        raise NotImplementedError

    async def handler(self):
        raise NotImplementedError

from typing import (
    Any,
    Literal,
    Union,
    List,
    Dict,
    Callable,
    overload
)
import pathlib
import asyncio

from .typings import (
    Routes,
    Listeners,
    Extensions,
    Shards,
    Awaitable
)
from .objects import Listener, Middleware, WebsocketRoute, Route
from .shards import Shard
from .settings import Settings
from .extensions import Extension
from .datastructures import URL
from .views import WebsocketHTTPView, HTTPView
from .request import Request
from .sockets import Websocket


_R = Callable[[Awaitable], Route]
_L = Callable[[Awaitable], Listener]
_V = Callable[[Awaitable], Union[HTTPView, WebsocketHTTPView]]
_M = Callable[[Awaitable], Middleware]

class Application:
    loop: asyncio.AbstractEventLoop
    url_prefix: str
    settings: Settings
    shards: Dict[str, Shard]
    views: Dict[str, Union[HTTPView, WebsocketHTTPView]]

    def __init__(self, 
            routes: Routes=...,
            listeners: Listeners=...,
            extensions: Extensions=...,
            shards: Shards=...,
            *,
            loop: asyncio.AbstractEventLoop=...,
            url_prefix: str=...,
            settings_file: Union[str, pathlib.Path]=...,
            load_settings_from_env: bool=...):
        ...

    async def wait_until_startup(self) -> None: ...
    @property
    def listeners(self) -> Dict[str, List[Awaitable]]: ...
    @property
    def extensions(self) -> Dict[str, Extension]: ...
    async def start(self,
                    host: str=...,
                    port: int=...,
                    *,
                    debug: bool=...) -> None: ...
    async def close(self) -> None: ...
    def run(self, *args, **kwargs) -> None: ...
    def add_route(self, route: Union[Route, WebsocketRoute]) -> Union[Route, WebsocketRoute]: ...
    def websocket(self, path: str) -> Callable[[Awaitable], WebsocketRoute]: ...
    def route(self, path: Union[str, URL], method: str) -> _R: ...
    def get(self, path: Union[str, URL]) -> _R: ...
    def put(self, path: Union[str, URL]) -> _R: ...
    def post(self, path: Union[str, URL]) -> _R: ...
    def delete(self, path: Union[str, URL]) -> _R: ...
    def head(self, path: Union[str, URL]) -> _R: ...
    def options(self, path: Union[str, URL]) -> _R: ...
    def patch(self, path: Union[str, URL]) -> _R: ...
    def add_listener(self, coro: Awaitable, name: str=...) -> Listener: ...
    def remove_listener(self, func: Awaitable=..., name: str=...) -> None: ...
    def listen(self, name: str=...) -> _L: ...
    async def dispatch(self, name: str, *args, **kwargs) -> Any: ...
    def register_shard(self, shard: Shard) -> Shard: ...
    def register_view(self, view: HTTPView) -> HTTPView: ...
    def register_websocket_view(self, view: WebsocketHTTPView) -> WebsocketHTTPView: ...
    def view(self, path: str) -> _V: ...
    def middleware(self, route: Route) -> _M: ...
    def register_extension(self, filepath: str) -> List[Extension]: ...
    def remove_extension(self, name: str) -> Extension: ...
    @overload
    async def wait_for(self, event: str, *, timeout: int =...) -> Any: ...
    @overload
    async def wait_for(self, route: Route, *, timeout: int=...) -> Request: ...
    @overload
    async def wait_for(self, event: Literal['data_receive'], *, timeout: int=...) -> bytes: ...
    @overload
    async def wait_for(self, event: Literal['request'], *, timeout: int=...) -> Request: ...
    @overload
    async def wait_for(self, event: Literal['data_sent'], *, timeout: int=...) -> bytes: ...
    @overload
    async def wait_for(self, event: Literal['connection_made'], *, timeout: int=...) -> Websocket: ...
    @overload
    async def wait_for(self, event: Literal['connection_lost'], *, timeout: int=...) -> None: ...
from typing import (
    AsyncIterator, 
    Coroutine, 
    Any, 
    Callable, 
    NamedTuple, 
    Protocol, 
    TypeVar, 
    Union, 
    Dict, 
    List, 
    Tuple, 
    TYPE_CHECKING,
    Literal,
    Optional
)
from os import PathLike

if TYPE_CHECKING:
    from .request import Request
    from .app import Application
    from .url import URL
    from .cookies import Cookie
    from .response import HTTPStatus
    from .objects import PartialRoute, Route
    from .responses import HTTPException

T = TypeVar('T')

Coro = Coroutine[Any, Any, T]
CoroFunc = Callable[..., Coro[T]]
Func = Callable[..., T]
MaybeCoroFunc = Callable[..., Union[T, Coro[T]]]
BytesLike = Union[bytes, bytearray, memoryview]
StrPath = Union[str, PathLike[str]]
BytesPath = Union[bytes, PathLike[bytes]]
OpenFile = Union[StrPath, BytesPath, int]

class Response(Protocol):
    async def prepare(self) -> bytes:
        ...

class Address(NamedTuple):
    host: str
    port: int

class Header(NamedTuple):
    name: str
    value: str

class NonStripedResult(NamedTuple):
    status_line: Literal[None]
    body: bytes
    headers: Dict[str, str]

class StripedResult(NamedTuple):
    status_line: str
    body: bytes
    headers: Dict[str, str]

class ParsedResult(NamedTuple):
    status_line: Optional[str]
    body: bytes
    headers: Dict[str, str]

StrURL = Union[str, 'URL']
_RouteResponse = Union[str, bytes, Dict[str, Any], List[Any], Response, 'URL', Any, AsyncIterator['ResponseBody']]
RouteResponse = Union[_RouteResponse, Tuple[_RouteResponse, int]]
RouteCallback = CoroFunc[RouteResponse]
ResponseBody = Union[str, bytes]
JSONResponseBody = Union[Dict[str, Any], List[Any]]
AnyBody = Union[ResponseBody, JSONResponseBody]
ResponseHeaders = Dict[str, str]
ResponseStatus = Union[int, 'HTTPStatus']
Cookies = Dict[str, 'Cookie']

CookieSessionCallback = Callable[['Request[Application]', Response], Union[str, bytes, bool]]
StatusCodeCallback = Callable[['Request[Application]', 'HTTPException', Union['Route', 'PartialRoute']], Coro[Any]]
ResponseMiddleware = Callable[['Request[Application]', Response, 'Route'], Coro[Any]]
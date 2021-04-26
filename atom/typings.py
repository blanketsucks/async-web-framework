import typing
import pathlib

from .shards import Shard
from .objects import Route, Listener

Routes = typing.List[Route]
Listeners = typing.List[Listener]
Extensions = typing.List[typing.Union[pathlib.Path, str]]
Shards = typing.List[Shard]
Awaitable = typing.Callable[..., typing.Coroutine]
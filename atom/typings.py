import typing
import pathlib

from .objects import Route, Listener

if typing.TYPE_CHECKING:
    from .shards import Shard

Routes = typing.List[Route]
Listeners = typing.List[Listener]
Extensions = typing.List[typing.Union[pathlib.Path, str]]
Shards = typing.List['Shard']
Awaitable = typing.Callable[..., typing.Coroutine]
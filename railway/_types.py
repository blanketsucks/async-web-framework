from typing import Coroutine, Any, Callable, TypeVar, Union

T = TypeVar('T')

Coro = Coroutine[Any, Any, Any]
CoroFunc = Callable[..., Coro]
Func = Callable[..., Any]
MaybeCoroFunc = Union[Callable[..., T], CoroFunc]
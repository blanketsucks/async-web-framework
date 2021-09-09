from typing import Any, Callable, Coroutine, Tuple, TypeVar, Union

T = TypeVar('T')
Coro = Coroutine[Any, Any, Any]
CoroFunc = Callable[..., Coro]
Func = Callable[..., Any]
MaybeCoroFunc = Union[Callable[..., T], CoroFunc]
peer = Tuple[str, int]
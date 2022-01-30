from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Any, TypeVar
import asyncio
import sys
import functools

PY310 = sys.version_info >= (3, 10)

if TYPE_CHECKING:
    T = TypeVar('T')

try:
    import uvloop  # type: ignore
    uvloop.install() # type: ignore
except ImportError:
    pass


def new_event_loop():
    return asyncio.new_event_loop()


def set_event_loop(loop: Any):
    asyncio.set_event_loop(loop)


def get_running_loop():
    return asyncio.get_running_loop()


def get_event_loop():
    return asyncio.get_event_loop()


def get_event_loop_policy():
    return asyncio.get_event_loop_policy()


async def run_in_thread(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    loop = get_running_loop()
    partial = functools.partial(func, *args, **kwargs)

    return await loop.run_in_executor(None, partial)

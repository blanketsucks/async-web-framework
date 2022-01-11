from __future__ import annotations

from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Any
import functools

from . import utils
from .types import CoroFunc
from .objects import Listener
from .errors import RegistrationError

if TYPE_CHECKING:
    from .app import Application

__all__ = 'EventListener',

class EventListener:
    def __init__(self) -> None:
        self._listeners: Dict[str, List[Listener]] = {}

    @property
    def listeners(self) -> List[Listener]:
        return [listener for listeners in self._listeners.values() for listener in listeners]

    def add_listener(self, name: str, callback: CoroFunc[Any]) -> Listener:
        if not utils.iscoroutinefunction(callback):
            raise RegistrationError('Listener callback must be a coroutine function')

        listener = Listener(callback, name)

        listeners = self._listeners.setdefault(name, [])
        listeners.append(listener)

        return listener

    def remove_listener(self, listener: Listener) -> None:
        listeners = self._listeners.get(listener.event)
        if not listeners:
            return

        listeners.remove(listener)

    def event(self, name: Optional[str] = None) -> Callable[[CoroFunc[Any]], Listener]:
        def decorator(callback: CoroFunc[Any]) -> Listener:
            return self.add_listener(name or callback.__name__, callback)
        return decorator

    def attach(self, app: Application) -> None:
        for listener in self.listeners:
            callback = functools.partial(listener.callback, app)
            app.add_event_listener(callback, listener.event)
    
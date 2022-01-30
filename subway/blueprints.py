from typing import Optional, Any

from .types import CoroFunc
from .objects import Listener
from .base import BaseApplication
from .router import Router
from .listeners import EventListener

__all__ = 'Blueprint',


class Blueprint(BaseApplication):
    def __init__(self, name: str, *, url_prefix: Optional[str] = None) -> None:
        self.name = name
        self.url_prefix = url_prefix or ''

        self.router = Router(self.url_prefix)
        self.listeners = EventListener()

    def __repr__(self) -> str:
        return f'<Blueprint name={self.name!r}>'

    def add_event_listener(self, callback: CoroFunc[Any], name: str) -> Listener:
        return self.listeners.add_listener(name, callback)

    def remove_event_listener(self, listener: Listener) -> None:
        return self.listeners.remove_listener(listener)

from typing import Tuple, Any, Dict, Type, List

from .objects import Route, Middleware, Listener

__all__ = (
    'InjectableMeta',
    'Injectable'
)

class InjectableMeta(type):
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs):
        routes = []
        listeners = []
        middlewares = []

        self = super().__new__(cls, name, bases, attrs, **kwargs)

        for base in reversed(self.__mro__):
            for elem, value in base.__dict__.items():
                if isinstance(value, Route):
                    routes.append(value)

                elif isinstance(value, Middleware):
                    middlewares.append(value)

                elif isinstance(value, Listener):
                    listeners.append(value)           

        self.__routes__ = routes
        self.__listeners__ = listeners
        self.__middlewares__ = middlewares

        return self

class Injectable:
    __routes__: List[Route]
    __listeners__: List[Listener]
    __middlewares__: List[Middleware]

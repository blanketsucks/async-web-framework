from typing import Tuple, Any, Dict, Type, List

from .objects import Route, Middleware, Listener

__all__ = (
    'InjectableMeta',
    'Injectable'
)

class InjectableMeta(type):
    """
    A meta class for injectable classes.
    """
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
    """
    A base class for injectable classes.

    Attributes:
        __routes__: A list of [Route](./objects.md) objects.
        __listeners__: A list of [Listener](./objects.md) objects.
        __middlewares__: A list of [Middleware](./objects.md) objects.

    Example:
        ```py
        import railway

        app = railway.Application()

        class MyInjectable(railway.Injectable, metaclass=railway.InjectableMeta):

            @railway.route('/')
            async def index(self, request: railway.Request):
                return 'Hello, world!'

        app.inject(MyInjectable())
        ```
    """
    __routes__: List[Route]
    __listeners__: List[Listener]
    __middlewares__: List[Middleware]

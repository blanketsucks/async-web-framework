"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from typing import Tuple, Any, Dict, Type, List, TYPE_CHECKING

from .objects import Route, Middleware, Listener

if TYPE_CHECKING:
    from .app import Application

__all__ = (
    'InjectableMeta',
    'Injectable'
)

class InjectableMeta(type):
    """
    A meta class for injectable classes.
    """
    __routes__: Dict[str, Route]
    __listeners__: List[Listener]
    __middlewares__: List[Middleware]
    __url_prefix__: str

    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs):
        routes: Dict[str, Route] = {}
        listeners = []
        middlewares = []

        url_prefix = kwargs.get('url_prefix', '')
        self = super().__new__(cls, name, bases, attrs, **kwargs)

        for base in reversed(self.__mro__):
            for elem, value in base.__dict__.items():
                if isinstance(value, Route):
                    path = url_prefix + value.path
                    routes[path] = value

                elif isinstance(value, Middleware):
                    middlewares.append(value)

                elif isinstance(value, Listener):
                    listeners.append(value)

        self.__url_prefix__ = url_prefix
        self.__routes__ = routes
        self.__listeners__ = listeners
        self.__middlewares__ = middlewares

        return self

class Injectable(metaclass=InjectableMeta):
    """
    A base class for injectable classes.

    Attributes
    ---------- 
    __routes__: List[:class:`~railway.objects.Route`]
        A list of :class:`~railway.objects.Route` objects.
    __listeners__: List[:class:`~railway.objects.Listener`]
        A list of :class:`~railway.objects.Listener` objects.
    __middlewares__: List[:class:`~railway.objects.Middleware`]
        A list of :class:`~railway.objects.Middleware` objects.

    Example
    -------
    .. code-block:: python3

        import railway

        app = railway.Application()

        class MyInjectable(railway.Injectable, metaclass=railway.InjectableMeta):

            @railway.route('/')
            async def index(self, request: railway.Request):
                return 'Hello, world!'

        app.inject(MyInjectable())
        
    """
    __routes__: Dict[str, Route]
    __listeners__: List[Listener]
    __middlewares__: List[Middleware]
    __url_prefix__: str



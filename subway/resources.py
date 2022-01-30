from typing import List, Tuple, Dict, Any, Type

from .objects import Route, Middleware, Listener

__all__ = (
    'ResourceMeta',
    "Resource",
)

class ResourceMeta(type):
    """
    A metaclass for resources.
    """
    __routes__: Dict[str, Route]
    __listeners__: List[Listener]
    __middlewares__: List[Middleware]
    __url_prefix__: str

    def __new__(cls, cls_name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs):
        attrs['__resource_name__'] = kwargs.get('name', cls_name)

        routes: Dict[str, Route] = {}
        listeners = []
        middlewares = []

        url_prefix = kwargs.get('url_prefix', '')
        self = super().__new__(cls, cls_name, bases, attrs, **kwargs)

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

class Resource(metaclass=ResourceMeta):
    """
    A resource to be subclassed and used.

    Example
    -------
    .. code-block:: python3

        import subway

        app = subway.Application()

        class MyResource(subway.Resource):

            @subway.route('/hello/{name}', 'GET')
            async def hello(self, request: subway.Request, name: str):
                return f'Hello, {name}!'

        app.add_resource(MyResource())
        
    """
    __routes__: Dict[str, Route]
    __listeners__: List[Listener]
    __middlewares__: List[Middleware]
    __url_prefix__: str
    __resource_name__: str
    
    def __repr__(self) -> str:
        return '<Resource name={0.name!r}>'.format(self)

    @property
    def name(self) -> str:
        """
        The name of the resource.
        """
        return self.__resource_name__

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError("name must be a string")
        
        self.__resource_name__ = value

    @property
    def routes(self) -> List[Route]:
        """
        The routes of the resource.
        """
        return list(self.__routes__.values())

    @property
    def listeners(self) -> List[Listener]:
        """
        The listeners of the resource.
        """
        return self.__listeners__

    @property
    def middlewares(self) -> List[Middleware]:
        """
        The middlewares of the resource.
        """
        return self.__middlewares__

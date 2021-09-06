from typing import List, Tuple, Dict, Any, Type

from .injectables import Injectable, InjectableMeta
from .objects import Route, Middleware, Listener

__all__ = (
    'ResourceMeta',
    "Resource",
)

class ResourceMeta(InjectableMeta):
    """
    A meta class for resources.
    """
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs):
        attrs['__resource_name__'] = kwargs.get('name', name)

        self = super().__new__(cls, name, bases, attrs)
        return self

class Resource(Injectable, metaclass=ResourceMeta):
    """
    A resource to be subclassed and used.

    Example:
        ```py
        import railway

        app = railway.Application()

        class MyResource(railway.Resource):

            @railway.route('/hello/{name}', 'GET')
            async def hello(self, request: railway.Request, name: str):
                return f'Hello, {name}!'

        app.add_resource(MyResource())
        ```
    """
    __resource_name__: str
    
    def __repr__(self) -> str:
        return '<Resource name={0.name!r}>'.format(self)

    @property
    def name(self) -> str:
        """
        Returns:
            The name of the resource.
        """
        return self.__resource_name__

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError("name must be a string")
        
        self.__resource_name__ = value

    def routes(self) -> List[Route]:
        """
        Returns:
            The list of registered routes in this resource.
        """
        return self.__routes__

    def middlewares(self) -> List[Middleware]:
        """
        Returns:
            The list of registered middlewares in this resource.
        """
        return self.__middlewares__

    def listeners(self) -> List[Listener]:
        """
        Returns:
            The list of registered listeners in this resource.
        """
        return self.__listeners__
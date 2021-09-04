from typing import List

from .meta import ResourceMeta
from .injectables import Injectable
from .objects import Route, Middleware, Listener

__all__ = (
    "Resource",
)

class Resource(Injectable, metaclass=ResourceMeta):
    __resource_name__: str
    
    def __repr__(self) -> str:
        return '<Resource name={0.name!r}>'.format(self)

    @property
    def name(self) -> str:
        return self.__resource_name__

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError("name must be a string")
        
        self.__resource_name__ = value

    def routes(self) -> List[Route]:
        return self.__routes__

    def middlewares(self) -> List[Middleware]:
        return self.__middlewares__

    def listeners(self) -> List[Listener]:
        return self.__listeners__
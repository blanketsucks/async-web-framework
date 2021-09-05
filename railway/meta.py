import inspect
from typing import List, Tuple, Any, Dict, Type

from .utils import VALID_METHODS
from ._types import CoroFunc
from .injectables import InjectableMeta

__all__ = (
    'ResourceMeta',
    'ViewMeta'
)

class ResourceMeta(InjectableMeta):
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs):
        attrs['__resource_name__'] = kwargs.get('name', name)

        self = super().__new__(cls, name, bases, attrs)
        return self

class ViewMeta(type):
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs: Any):
        attrs['__url_route__'] = kwargs.get('path', '')

        self = super().__new__(cls, name, bases, attrs)
        view_routes: List[CoroFunc] = []

        for base in self.mro():
            for _, value in base.__dict__.items():
                if inspect.iscoroutinefunction(value):
                    if value.__name__.upper() in VALID_METHODS:
                        view_routes.append(value)

        self.__routes__ = view_routes
        return self

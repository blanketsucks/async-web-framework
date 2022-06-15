from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, Any
from abc import ABC, abstractmethod

from .request import Request

if TYPE_CHECKING:
    from .app import Application

T = TypeVar('T')

__all__ = (
    'AbstractParameterConverter',
    'AbstractBodyConverter',
)

class AbstractParameterConverter(ABC, Generic[T]):
    if TYPE_CHECKING:
        def __getattr__(self, name: str) -> Any: ...

    @abstractmethod
    async def convert(self, request: Request[Application], argument: str) -> T:
        raise NotImplementedError

class AbstractBodyConverter(ABC, Generic[T]):
    if TYPE_CHECKING:
        def __getattr__(self, name: str) -> Any: ...

    @abstractmethod
    async def convert(self, request: Request[Application], body: bytes) -> T:
        raise NotImplementedError



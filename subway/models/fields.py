from __future__ import annotations

from collections.abc import Sequence, Mapping, MutableMapping, Iterable
from typing import TYPE_CHECKING, Any, Callable, Optional, Literal, Set, Type, TypeVar, Union, Generic

from .utils import DEFAULT

T = TypeVar('T')

if TYPE_CHECKING:
    from .models import Model

__all__ = 'Field', 'field', 'validator'

LIST_LIKE_TYPES = (Iterable, Sequence, list, set, Set, frozenset)
DICT_TYPES = (Mapping, MutableMapping, dict)

def validator(field: str) -> Callable[..., Any]:
    def callback(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__validator__ = field
        return func

    return callback

class Field(Generic[T]):
    def __init__(
        self, 
        *,
        default: Any = DEFAULT, 
        default_factory: Type[Any] = DEFAULT,
        strict: bool = False,
        name: Optional[str] = None, 
        validator: Optional[Callable[[Model, T, Field[T]], Any]] = None
    ) -> None:
        self.name = name
        self.default = default
        self.default_factory = default_factory
        self.strict = strict
        self.validator = validator or (lambda _, value, field: value)

        self._annotation: Any = None

    def __repr__(self) -> str:
        return f'<Field name={self.name!r} default={self.default!r} strict={self.strict!r}>'

    @property
    def annotation(self) -> Any:
        return self._annotation

    @annotation.setter
    def annotation(self, value: Any) -> None:
        self._annotation = value

    @staticmethod
    def has_args(annotation: Any) -> bool:
        args = getattr(annotation, '__args__', None)
        if not args:
            return False

        return True

    @staticmethod
    def any_or_object(value: Any) -> Any:
        return object if value is Any else value

    def evaluate(self, value: Any, *, annotation: Optional[Any] = None) -> bool:
        ann: Any = annotation or self.annotation
        origin = getattr(annotation, '__origin__', None)

        if origin is Union:
            if type(None) in ann.__args__:
                expected, _ = ann.__args__
                return isinstance(value, expected) or value is None

            return any(self.evaluate(value, annotation=typ) for typ in ann.__args__)

        if origin is not None:
            if not isinstance(value, origin):
                return False
            else:
                if not self.strict:
                    return True

            if not self.has_args(ann):
                return True
        else:
            return isinstance(value, self.any_or_object(ann))

        if origin is Literal:
            if value not in ann.__args__:
                return False

            return True
        elif origin in LIST_LIKE_TYPES:
            expected = self.any_or_object(ann.__args__[0])
            return all(isinstance(v, expected) for v in value)
        elif origin is tuple:
            has_ellipsis = ann.__args__[-1] is ...
            expected = ann.__args__[:-1] if has_ellipsis else ann.__args__
            elements = len(expected)

            if has_ellipsis:
                expected = self.any_or_object(expected[0])
            else:
                expected = tuple(self.any_or_object(e) for e in expected)

            if len(value) != elements and not has_ellipsis:
                return False

            if has_ellipsis:
                return all(isinstance(v, expected) for v in value)
            else:
                return all(isinstance(value[i], typ) for i, typ in enumerate(expected))
        elif origin in DICT_TYPES:
            pair = ann.__args__
            key_type, value_type = pair[0], self.any_or_object(pair[1])

            return all(isinstance(k, key_type) and isinstance(v, value_type) for k, v in value.items())

        raise RuntimeError(f'Unsupported annotation type: {origin}')

def field(
    *,
    default: Any = DEFAULT, 
    default_factory: Type[Any] = DEFAULT,
    strict: bool = False,
    name: Optional[str] = None, 
    validator: Optional[Callable[[Model, Any, Field[Any]], Any]] = None
) -> Any:
    if default is not DEFAULT and default_factory is not DEFAULT:
        raise ValueError('Cannot specify both default and default_factory')

    return Field(default=default, default_factory=default_factory, strict=strict, name=name, validator=validator)
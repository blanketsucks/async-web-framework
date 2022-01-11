from typing import Any, Callable, Optional, Literal, Union

__all__ = 'Field',

class Field:
    def __init__(
        self, 
        name: str, 
        annotation: Any, 
        default: Any, 
        strict: bool = False,
        *,
        validator: Callable[..., None]
    ) -> None:
        self.name = name
        self.annotation = annotation
        self.default = default
        self.strict = strict
        self.validator = validator

    def __repr__(self) -> str:
        return f'<Field name={self.name!r} default={self.default!r} strict={self.strict!r}>'

    @staticmethod
    def has_args(annotation: Any) -> bool:
        args = getattr(annotation, '__args__', None)
        if not args:
            return False

        return True

    @staticmethod
    def any_or_object(value: Any) -> Any:
        return object if value is Any else value

    @staticmethod
    def validate(name: str):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            func.__name__ = f'_validate_{name}_'
            return func
        return decorator

    def is_valid(self, value: Any, *, typ: Optional[Any] = None) -> bool:
        annotation = typ or self.annotation
        origin = getattr(annotation, '__origin__', None)

        if origin is Union and type(None) in annotation.__args__:
            expected, _ = annotation.__args__
            return isinstance(value, expected) or value is None

        if origin is not None:
            if not isinstance(value, origin):
                return False
            else:
                if not self.strict:
                    return True

            if not self.has_args(annotation):
                return True
        else:
            return isinstance(value, self.any_or_object(annotation))

        if origin is Literal:
            if value not in annotation.__args__:
                return False

            return True
        elif origin is list:
            expected = self.any_or_object(annotation.__args__[0])
            return all(isinstance(v, expected) for v in value)
        elif origin is tuple:
            has_ellipsis = annotation.__args__[-1] is ...
            expected = annotation.__args__[:-1] if has_ellipsis else annotation.__args__
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
        elif origin is dict:
            pair = annotation.__args__
            key_type, value_type = pair[0], self.any_or_object(pair[1])

            return all(isinstance(k, key_type) and isinstance(v, value_type) for k, v in value.items())

        return any(self.is_valid(value, typ=typ) for typ in annotation.__args__)
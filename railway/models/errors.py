from typing import Dict, Any

from .fields import Field

__all__ = (
    'ModelError',
    'IncompatibleType',
    'MissingField',
    'ObjectNotSerializable',
)


class ModelError(Exception):
    pass

class IncompatibleType(ModelError):
    def __init__(self, field: Field, argument: Any, data: Dict[str, Any]) -> None:
        self.field = field
        self.data = data
        self.argument = argument

        message = f'Incompatible type {argument.__name__!r} for {field.name!r}'
        super().__init__(message)


class MissingField(ModelError):
    def __init__(self, field: Field, data: Dict[str, Any]) -> None:
        self.field = field
        self.data = data

        message = f'Missing field {field.name!r}'
        super().__init__(message)


class ObjectNotSerializable(Exception):
    def __init__(self, obj: Any) -> None:
        self.obj = obj

        message = f'Object {obj!r} is not JSON serializable'
        super().__init__(message)

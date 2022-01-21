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
    def __init__(self, field: Field, argument: Any) -> None:
        self.field = field
        self.argument = argument
        
        super().__init__(f'Incompatible type {argument.__name__!r} for {field.name!r}')


class MissingField(ModelError):
    def __init__(self, field: Field) -> None:
        self.field = field
        super().__init__(f'Missing field {field.name!r}')


class ObjectNotSerializable(Exception):
    def __init__(self, obj: Any) -> None:
        self.obj = obj
        super().__init__(f'Object {obj!r} is not JSON serializable')

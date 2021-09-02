from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple, Type, Union

__all__ = (
    'Field',
    'Model',
    'IncompatibleType',
    'MissingField',
    'ModelMeta'
)


class _Default:
    def __repr__(self):
        return '<Default>'

_default = _Default()

class IncompatibleType(Exception):
    def __init__(self, field: Field, argument: Type[Any], data: Dict[str, Any]) -> None:
        self.field = field
        self.data = data
        self.argument = argument

        message = f'Incompatible type {argument} for argument {field.name!r} which accepts {field.type}'
        super().__init__(message)

class MissingField(Exception):
    def __init__(self, field: Field, data: Dict[str, Any]) -> None:
        self.field = field
        self.data = data

        message = f'Missing field {field.name!r}'
        super().__init__(message)

def _make_fn(name: str, body: str) -> Callable[..., None]:
    txt = f"def __create_fn__():\n {body}\n return {name}"

    ns: Dict[str, Any] = {}
    exec(txt, {}, ns)

    return ns['__create_fn__']()

def _make_init(annotations: Dict[str, Type[Any]], defaults: Dict[str, Any]) -> str:
    names: List[str] = []
    args: List[str] = []

    for name, annotation in annotations.items():
        default = defaults.get(name, _default)
        names.append(name)

        if isinstance(default, _Default):
            args.append(f'{name}: {annotation}')
        else:
            args.append(f'{name}: {annotation}={default}')

    body: List[str] = []

    for arg in names:
        body.append(f'self.{arg} = {arg}')

    actual = ', '.join(args)
    bdy = '\n'.join(f'  {b}' for b in body)

    return f'def __init__(self, *, {actual}) -> None:\n{bdy}'

def _make_fields(annotations: Dict[str, Type[Any]], defaults: Dict[str, Any]) -> Tuple[Field, ...]:
    fields: List[Field] = []

    for name, annotation in annotations.items():
        annotation = eval(annotation)

        if origin := getattr(annotation, '__origin__', None):
            if origin is Union:
                types = annotation.__args__

                if type(None) in types:
                    defaults[name] = None

        default = defaults.get(name, _default)

        field = Field(name, annotation, default)
        fields.append(field)

    return tuple(fields)


def _getattr(obj: Any, name: str):
    attr = getattr(obj, name)

    if isinstance(attr, Model):
        return attr.json()

    return attr

def _get_repr(obj: Any, name: str):
    attr = getattr(obj, name)
    if isinstance(attr, Model):
        return f'{name}={repr(attr)}'

    return f'{name}={attr!r}'

class Field:
    def __init__(self, name: str, type: Type[Any], default: Any):
        self.name = name
        self.type = type
        self.default = default

    def __repr__(self) -> str:
        return '<Field type={0.type} name={0.name!r}>'.format(self)

    def __str__(self):
        return self.name

class ModelMeta(type):
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any]):
        annotations = attrs.get('__annotations__')
        defaults: Dict[str, Any] = {}

        if annotations:
            for key, _ in annotations.items():
                value = attrs.get(key, _default)

                if not isinstance(value, _Default):
                    defaults[key] = value

            fields = _make_fields(annotations, defaults)
            body = _make_init(annotations, defaults)

            fn = _make_fn('__init__', body)
            fn.__qualname__ = f'{name}.__init__'

            attrs['__fields__'] = fields
            attrs['__init__'] = fn

            return super().__new__(cls, name, bases, attrs)

        attrs['__fields__'] = ()
        return super().__new__(cls, name, bases, attrs)

class Model(metaclass=ModelMeta):
    if TYPE_CHECKING:
        __fields__: Tuple[Field]

    def __init__(self, **kwargs: Any) -> None:
        pass

    def __repr__(self) -> str:
        attrs = [_get_repr(self, field.name) for field in self.__fields__]
        return f'<{self.__class__.__name__} {" ".join(attrs)}>'

    def json(self) -> Dict[str, Any]:
        return {f.name: _getattr(self, f.name) for f in self.__fields__}

    @classmethod
    def from_json(cls, data: Union[Dict[str, Any], Any]):
        if not isinstance(data, dict):
            ret = f"Invalid argument type for 'data'. Expected {dict!r} got {data.__class__!r} instead"
            raise TypeError(ret)

        kwargs = {}

        for field in cls.__fields__:
            if field.name in data:
                try:
                    if issubclass(field.type, Model):
                        kwargs[field.name] = field.type(**data[field.name])

                    else:
                        kwargs[field.name] = field.type(data[field.name])
                except (ValueError, TypeError):
                    argument = data[field.name]
                    type = argument.__class__

                    raise IncompatibleType(field, type, data) from None

            else:
                if isinstance(field.default, _Default):
                    raise MissingField(field, data)

                kwargs[field.name] = field.default

        return cls(**kwargs)


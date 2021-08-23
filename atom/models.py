from typing import TYPE_CHECKING, Any, Callable, Dict, Tuple, Type, TypeVar

__all__ = (
    'Field',
    'Model'
)

_T = TypeVar('_T')

class IncompatibleType(Exception):
    def __init__(self, name: str, accepts: Type, argument: Type) -> None:
        self.name = name
        self.accepts = accepts
        self.argument = argument

        message = f'Incompatible type {argument} for argument {name!r} which accepts {accepts}'
        super().__init__(message)

def _make_fn(name: str, body: str) -> Callable:
    txt = f"def __create_fn__():\n {body}\n return {name}"

    ns = {}
    exec(txt, {}, ns)

    return ns['__create_fn__']()

def _make_init(annotations: Dict[str, Type]) -> str:
    names = []
    args = []

    for name, annotation in annotations.items():
        names.append(name)
        args.append(f'{name}: {annotation}')

    body = []

    for arg in names:
        body.append(f'self.{arg} = {arg}')

    args = ', '.join(args)
    body = '\n'.join(f'  {b}' for b in body)

    return f'def __init__(self, *, {args}):\n{body}'

def _make_fields(annotations: Dict[str, Type]):
    fields = []

    for name, annotation in annotations.items():
        field = Field(name, eval(annotation))
        fields.append(field)

    return tuple(fields)

def _getattr(obj, name: str):
    attr = getattr(obj, name)

    if isinstance(attr, Model):
        return attr.json()

    return attr

def _get_repr(obj, name: str):
    attr = getattr(obj, name)
    if isinstance(attr, Model):
        return f'{name}={repr(attr)}'

    return f'{name}={attr!r}'

class Field:
    def __init__(self, name: str, type: Type):
        self.name = name
        self.type = type

    def __repr__(self) -> str:
        return '<Field type={0.type} name={0.name!r}>'.format(self)

    def __str__(self):
        return self.name

class ModelMeta(type):
    def __new__(cls, name: str, bases: Tuple[Type], attrs: Dict[str, Any], **kwargs):
        annotations = attrs.get('__annotations__')

        if annotations:
            body = _make_init(annotations)
            fields = _make_fields(annotations)

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

    def __init__(self, **kwargs) -> None:
        pass

    def __repr__(self) -> str:
        attrs = [_get_repr(self, field.name) for field in self.__fields__]
        return f'<{self.__class__.__name__} {" ".join(attrs)}>'

    def json(self) -> Dict[str, Any]:
        return {f.name: _getattr(self, f.name) for f in self.__fields__}

    @classmethod
    def from_json(cls: Type[_T], data: Dict[str, Any]) -> _T:
        for field in cls.__fields__:
            if field.name in data:
                try:
                    if issubclass(field.type, Model):
                        data[field.name] = field.type(**data[field.name])

                    else:
                        data[field.name] = field.type(data[field.name])
                except (ValueError, TypeError):
                    name = field.name
                    accepts = field.type

                    argument = data[name]
                    type = argument.__class__

                    raise IncompatibleType(name, accepts, type) from None

        return cls(**data)

class User(Model):
    id: int

user = User.from_json({'id': '123'})
print(user)

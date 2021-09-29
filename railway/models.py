"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations
import builtins
from typing import (
    TYPE_CHECKING, 
    Any, 
    Callable, 
    Dict, 
    Iterable, 
    List, 
    Tuple, 
    Type, 
    Union, 
    Iterator, 
    Optional
)
import json
import inspect
import sys

from .utils import get_union_args

__all__ = (
    'Field',
    'Model',
    'IncompatibleType',
    'MissingField',
    'ObjectNotSerializable',
    'ModelMeta',
    'ModelOptions',
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

        types = [f'{type.__name__!r}' for type in field.types]

        message = f'Incompatible type {argument.__name__!r} for {field.name!r} which accepts {", ".join(types)}'
        super().__init__(message)

class MissingField(Exception):
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

def _make_fn(name: str, body: str) -> Callable[..., None]:
    txt = f"def __create_fn__():\n {body}\n return {name}"

    ns: Dict[str, Any] = {}
    exec(txt, {}, ns)

    return ns['__create_fn__']()

def _make_init(fields: Tuple[Field, ...], defaults: Dict[str, Any]) -> str:
    names: List[str] = []
    args: List[str] = []

    for field in fields:
        default = defaults.get(field.name, _default)
        names.append(field.name)

        actual = [type.__name__ for type in field.types]

        if len(actual) == 1:
            annotation = actual[0]
        else:
            annotation = f'typing.Union[{", ".join(actual)}]'

        if isinstance(default, _Default):
            args.append(f'{field.name}: {annotation}')
        else:
            args.append(f'{field.name}: {annotation}={default!r}')

    body: List[str] = []

    for arg in names:
        body.append(f'self.{arg} = {arg}')

    actual = ', '.join(args)
    bdy = '\n'.join(f'  {b}' for b in body)
    
    return f'def __init__(self, *, {actual}) -> None:\n{bdy}'

def _make_fields(annotations: Dict[str, Type[Any]], defaults: Dict[str, Any]) -> Tuple[Field, ...]:
    fields: List[Field] = []

    for name, annotation in annotations.items():
        if type(None) in annotation:
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

def _is_json_serializable(obj: Any) -> bool:
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False

def _get_repr(obj: Any, name: str):
    attr = getattr(obj, name)
    if isinstance(attr, Model):
        return f'{name}={repr(attr)}'

    return f'{name}={attr!r}'

def _get_model_from_bases(bases: Tuple[Type]):
    for base in bases:
        if issubclass(base, Model) or base is Model:
            return base

def _transform(field: Field, data: Dict[str, Any]):
    value = data[field.name]
    transformed = None

    for type in field.types:
        try:
            if issubclass(type, Model):
                transformed = type.from_json(value)
            else:
                transformed = type(value)
        except (ValueError, TypeError, MissingField):
            continue

    if transformed is None:
        raise IncompatibleType(field, value.__class__, data)

    return transformed

def _get_real_annotation(value: str) -> Type:
    try:
        ret = eval(value)
    except NameError:
        ret = value
    else:
        if isinstance(ret, type):
            return ret

    frame = sys._getframe(2)

    locals = frame.f_locals
    globals = frame.f_globals

    if (_type := getattr(builtins, ret, None)):
        return _type

    if ret in locals:
        return locals[ret]

    if ret in globals:
        return globals[ret]

    raise RuntimeError(f'Could not parse stringed annotation: {value!r}')

class Field:
    """
    A model field.

    Attributes
    ----------
    name: :class:`str`
        The name of the field.
    type: :class:`type`
        The type of the field.
    default: Any
        The default value of the field.
    """
    def __init__(self, name: str, types: Tuple[Type], default: Any):
        self.name = name
        self.types = types
        self.default = default

    def __repr__(self) -> str:
        return '<Field name={0.name!r}>'.format(self)

    def __str__(self):
        return self.name

    def __iter__(self):
        return iter(self.types)

    def __eq__(self, o: Any) -> bool:
        if not isinstance(o, Field):
            return NotImplemented

        return (self.name, self.types, self.default) == (o.name, o.types, o.default)

class ModelOptions:
    """
    Options for a model.

    Attributes
    ----------
    include_null_fields: :class:`bool`
        Whether to include null fields in the serialized output.
    repr: :class:`bool`
        Whether or not to return a custom repr.
    """
    def __init__(self, **options) -> None:
        self.include_null_fields: bool = options.get('include_null_fields', True)
        self.repr = options.get('repr', True)
        self.name = options.get('name', None)

class ModelMeta(type):
    def __new__(cls, name: str, bases: Tuple[Type[Any]], attrs: Dict[str, Any], **kwargs):
        old = attrs.get('__annotations__', {})
        annotations = {}

        for key, value in old.items():
            if isinstance(value, str):
                annotation = _get_real_annotation(value)
            else:
                annotation = value

            annotations[key] = get_union_args(annotation)

        defaults: Dict[str, Any] = {}

        if annotations:
            parent = _get_model_from_bases(bases)

            for key, _ in annotations.items():
                value = attrs.get(key, _default)

                if not isinstance(value, _Default):
                    defaults[key] = value

            fields = _make_fields(annotations, defaults) + (() if parent is None else parent.__fields__)
            body = _make_init(fields, defaults)

            fn = _make_fn('__init__', body)

            fn.__qualname__ = f'{name}.__init__'
            kwargs.setdefault('name', name)

            attrs['__fields__'] = fields
            attrs['__field_mapping__'] = {field.name: field for field in fields}
            attrs['__init__'] = fn
            attrs['__parent__'] = parent
            attrs['__children__'] = []
            attrs['__options__'] = ModelOptions(**kwargs)
            attrs['__name__'] = kwargs['name']

            self = super().__new__(cls, name, bases, attrs)
            if hasattr(parent, '__children__'):
                parent.__children__.append(self) # type: ignore

            return self
        
        parent = None
        if name == 'Model' and not bases:
            attrs['__parent__'] = cls
        else:
            parent = _get_model_from_bases(bases)
            attrs['__parent__'] = parent
        
        attrs['__children__'] = []
        attrs['__fields__'] = parent.__fields__ if parent else ()
        attrs['__field_mapping__'] = parent.__field_mapping__ if parent else {}
        attrs['__options__'] = ModelOptions(**kwargs)

        self = super().__new__(cls, name, bases, attrs)
        if hasattr(parent, '__children__'):
            parent.__children__.append(self) # type: ignore

        return self

    def __iter__(self):
        return iter(self.__fields__) # type: ignore

    def __eq__(self, o: Any) -> bool:
        if not isinstance(o, ModelMeta):
            return NotImplemented

        return self.__fields__ == o.__fields__ # type: ignore
 
class Model(metaclass=ModelMeta):
    """
    A model that contains fields and methods to serialize and deserialize it into JSON objects.

    Example
    -------
    .. code-block:: python3

        from railway import Model

        class Person(Model):
            name: str
            age: int

        jim = Person(name='Jim', age=18)
        print(jim)
        print(jim.json())

        alex = Person.from_json({'name': 'Alex', 'age': 20})
        print(alex)
        print(alex.json())
    """
    if TYPE_CHECKING:
        __fields__: Tuple[Field]
        __field_mapping__: Dict[str, Field]
        __options__: ModelOptions
        __parent__: Type[Model]
        __children__: List[Type[Model]]

    def __repr__(self) -> str:
        if not self.options.repr:
            return super().__repr__()

        attrs = [_get_repr(self, field.name) for field in self.__fields__]
        return f'<{self.__class__.__name__} {" ".join(attrs)}>'

    def __iter__(self) -> Iterator[Tuple[Field, Any]]:
        return self._iter()

    def __setattr__(self, name: str, value: Any) -> None:
        field = self.get_field(name)
        if not field:
            raise AttributeError(name)

        if not isinstance(value, field.types):
            if value != field.default:
                raise IncompatibleType(field, value.__class__, value)
            
        super().__setattr__(name, value)

    def __getitem__(self, name: str) -> Tuple[Field, Any]:
        field = self.get_field(name)
        if not field:
            raise KeyError(name)

        return field, getattr(self, name)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Model):
            return NotImplemented

        return self.json() == other.json()

    @classmethod
    def from_json(cls, data: Union[Dict[str, Any], Any]) -> Model:
        """
        Makes the model from a JSON object.

        Parameters
        -----------
        data: :class:`dict`
            The JSON object.

        Raises
        ------
        TypeError: If the data passed in is not a dict.
        MissingField: If a field is missing.
        IncompatibleType: If the type of the field is incompatible with the type of the data.
        """
        if not isinstance(data, dict):
            ret = f"Invalid argument type for 'data'. Expected {dict!r} got {data.__class__!r} instead"
            raise TypeError(ret)

        kwargs = {}

        for field in cls.__fields__:
            if field.name in data:
                kwargs[field.name] = _transform(field, data)
            else:
                if isinstance(field.default, _Default):
                    raise MissingField(field, data)

                kwargs[field.name] = field.default

        return cls(**kwargs)

    @classmethod
    def get_field(cls, name: str) -> Optional[Field]:
        """
        Get a field by name.

        Parameters
        ----------
        name: :class:`str`
            The name of the field.
        """
        return cls.__field_mapping__.get(name)

    @property
    def fields(self) -> Tuple[Field]:
        """
        The fields of the model.
        """
        return self.__fields__

    @property
    def options(self) -> ModelOptions:
        """
        The options of the model.
        """
        return self.__options__

    @property
    def parent(self) -> Type[Model]:
        """
        The parent of the model.
        """
        return self.__parent__

    @property
    def children(self) -> List[Type[Model]]:
        """
        The children of the model.
        """
        return self.__children__

    @property
    def signature(self) -> inspect.Signature:
        """
        The signature of the model.
        """
        return inspect.signature(self.__init__)

    def is_json_serializable(self) -> bool:
        """
        Checks if the model is JSON serializable.
        """
        for field in self.__fields__:
            value = _getattr(self, field.name)
            if not _is_json_serializable(value):
                return False

        return True

    def copy(self) -> 'Model':
        """
        Returns a copy of the model.
        """
        data = self.json()
        return self.from_json(data)

    def json(self, *, include: Iterable[str]=None, exclude: Iterable[str]=None) -> Dict[str, Any]:
        """
        Serializes the model into a JSON object.

        Parameters
        -----------
        include: Tuple[:class:`str`, ...]
            The names of the fields to include. Defaults to all of the model's fields.
        exclude: Tuple[:class:`str`, ...]
            The names of the fields to exclude.
        """
        data = {}

        for field, value in self._iter(include, exclude):
            if isinstance(value, Model):
                if not value.is_json_serializable():
                    raise ObjectNotSerializable(value)

                data[field.name] = value.json()
                continue


            if not _is_json_serializable(value):
                raise ObjectNotSerializable(value)

            data[field.name] = value

        return data

    def to_dict(self, *, include: Iterable[str]=None, exclude: Iterable[str]=None) -> Dict[str, Any]:
        """
        Serializes the model into a dictionary.
        The value returned may not be JSON serializable.

        Parameters
        -----------
        include: Tuple[:class:`str`, ...]
            The names of the fields to include. Defaults to all of the model's fields.
        exclude: Tuple[:class:`str`, ...]
            The names of the fields to exclude.
        """
        data = {}

        for field, value in self._iter(include, exclude):
            if isinstance(value, Model):
                value = value.to_dict()

            data[field.name] = value

        return data

    def _iter(self, include: Iterable[str]=None, exclude: Iterable[str]=None):
        if include is None:
            include = [field.name for field in self.__fields__]
        
        if exclude is None:
            exclude = []

        include_null = self.options.include_null_fields

        for field in self.fields:
            if field.name in exclude or field.name not in include:
                continue

            value = getattr(self, field.name)
            if not include_null and value is None:
                continue

            yield field, value

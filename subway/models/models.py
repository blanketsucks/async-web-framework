from typing import (
    Any, 
    Dict, 
    List, 
    Sequence, 
    Tuple, 
    Type, 
    TypedDict, 
    TYPE_CHECKING, 
    Optional, 
    Union, 
    Iterable, 
    Callable, 
    Iterator, 
    TypeVar
)

from subway.utils import evaluate_annotation, __dataclass_transform__
from .utils import DEFAULT, is_json_serializable, is_optional, safe_getattr
from .fields import Field, field
from .errors import IncompatibleType, ObjectNotSerializable, MissingField

ModelT = TypeVar('ModelT', bound='Model')

__all__ = (
    'ModelOptions',
    'ModelMeta',
    'Model',
)


def noop(*_: Any) -> bool:
    return True

class ModelOptions(TypedDict):
    strict: bool
    strict_fields: Union[List[str], Tuple[str]]
    include_null_fields: bool
    slotted: bool

def find_validator(name: str, namespace: Dict[str, Any]) -> Callable[..., bool]:
    for value in namespace.values():
        if hasattr(value, '__validator__') and value.__validator__ == name:
            return value

    return noop

def create_fields(
    annotations: Dict[str, Any], 
    defaults: Dict[str, Any],
    namespace: Dict[str, Any],
    options: ModelOptions
) -> List[Field[Any]]:
    fields: List[Field[Any]] = []

    for key, annotation in annotations.items():
        if isinstance(namespace.get(key), Field):
            field = namespace[key]
            field.name = key

            if field.strict:
                strict = options['strict_fields']
                if isinstance(strict, tuple):
                    strict += (key,)
                if isinstance(strict, list):
                    strict.append(key)
            else:
                if options['strict'] is True:
                    raise ValueError(f'Field {key!r} is not strict')

        else:
            default = defaults[key]
            validator = find_validator(key, namespace)

            field = Field(default=default, name=key, validator=validator)

            if options['strict'] is True or field.name in options['strict_fields']:
                field.strict = True

        field.annotation = annotation
        fields.append(field)
    
    return fields

def get_model_bases(bases: Tuple[Any, ...]) -> Iterator['ModelMeta']:
    for base in bases:
        if issubclass(base, Model):
            yield base
        else:
            yield from get_model_bases(base.__bases__)

@__dataclass_transform__(kw_only_default=True, field_descriptors=(Field, field))
class ModelMeta(type):
    if TYPE_CHECKING:
        __fields__: List[Field[Any]]
        __field_mapping__: Dict[str, Field[Any]]
        __options__: ModelOptions

    def __new__(cls, name: str, bases: Tuple[Any, ...], attrs: Dict[str, Any], **kwargs: Any):
        options: ModelOptions = {
            'strict': kwargs.get('strict', False),
            'strict_fields': attrs.get('__strict_fields__', []),
            'include_null_fields': kwargs.get('include_null_fields', False),
            'slotted': kwargs.get('slotted', False),
        }

        old = attrs.get('__annotations__', {})

        defaults: Dict[str, Any] = {}
        slots: List[str] = []
        annotations: Dict[str, Any] = {}

        for key, value in old.items():
            if isinstance(value, str):
                value = evaluate_annotation(value, stacklevel=1)

            annotations[key] = value

            default = attrs.get(key, DEFAULT)
            if is_optional(value):
                default = None

            if default is not DEFAULT and options['slotted']:
                raise TypeError('Cannot use default values with slotted models. Use Optional[T] instead.')

            defaults[key] = default

        if kwargs.get('strict', False) and attrs.get('__strict_fields__', None):
            raise ValueError('__strict_fields__ cannot be used with strict=True')

        fields = create_fields(annotations, defaults, attrs, options)
        for model in get_model_bases(bases):
            fields.extend(model.__fields__)

        kwargs.setdefault('name', name)

        attrs['__options__'] = options
        attrs['__fields__'] = fields
        attrs['__field_mapping__'] = {field.name: field for field in fields}

        if options['slotted'] is True:
            attrs['__slots__'] = tuple(field.name for field in fields)

        return super().__new__(cls, name, bases, attrs)

    def __iter__(self):
        return iter(self.__fields__)

    def __eq__(self, o: Any) -> bool:
        if not isinstance(o, ModelMeta):
            return NotImplemented

        return self.__fields__ == o.__fields__

    def __hash__(self):
        return hash(self.__fields__)

    def get_field(self, name: str) -> Optional[Field[Any]]:
        """
        Get a field by name.

        Parameters
        ----------
        name: :class:`str`
            The name of the field.
        """
        return self.__field_mapping__.get(name)

    def add_field(self, field: Field) -> None:
        """
        Add a field to the model.

        Parameters
        ----------
        field: :class:`Field`
            The field to add.
        """
        assert field.name, 'Field name cannot be empty'
        if self.options['slotted']:
            raise TypeError('Cannot add extra fields to slotted models')

        self.__fields__.append(field)
        self.__field_mapping__[field.name] = field

    @property
    def options(self) -> ModelOptions:
        return self.__options__

    @property
    def fields(self) -> List[Field]:
        return self.__fields__

class Model(metaclass=ModelMeta):
    """
    A model that contains fields and methods to serialize and deserialize it into JSON objects.

    Example
    -------
        Basic Example ::

            from subway import Model

            class Person(Model):
                name: str
                age: int

            jim = Person(name='Jim', age=18)
            print(jim)
            print(jim.json())

            alex = Person.from_json({'name': 'Alex', 'age': 20})
            print(alex)
            print(alex.json())

        It can also be used as the following ::

            from subway import Model, Application, Request

            app = Application()

            class User(Model):
                name: str

            @app.route('/users', 'POST')
            async def create_user(request: Request, user: User):
                print(user)
                print(user.name)

                return user


    """
    if TYPE_CHECKING:
        __fields__: List[Field]
        __field_mapping__: Dict[str, Field]
        __options__: ModelOptions

    def __init__(self, **kwargs: Any) -> None:
        for field in self.fields:
            assert field.name
            value = kwargs.get(field.name, field.default)

            if value is DEFAULT:
                if field.default_factory is not None:
                    setattr(self, field.name, field.default_factory())
                else:
                    raise MissingField(field)
                
                continue

            setattr(self, field.name, value)

    def _get_repr(self, obj: Any, name: str):
        attr = getattr(obj, name)
        if not self.options['include_null_fields'] and attr is None:
            return None

        if isinstance(attr, Model):
            return f'{name}={repr(attr)}'

        return f'{name}={attr!r}'

    def __iter__(self) -> Iterator[Tuple[Field[Any], Any]]:
        """
        Iterates over the fields and their values.
        """
        return self._iter()

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Set a field's value.

        Parameters
        ----------
        name: :class:`str`
            The name of the field.
        value: Any
            The value to set.

        Raises
        ------
        AttributeError
            If the field does not exist.
        IncompatibleType
            If the value's type is incompatible with the field's.
        """
        cls = type(self)
        field = cls.get_field(name)

        if not field:
            raise AttributeError(name)

        if not field.evaluate(value):
            if value != field.default:
                raise IncompatibleType(field, value.__class__)

        ret = field.validator(self, value, field)
        super().__setattr__(name, ret)

    def __getitem__(self, name: str) -> Tuple[Field[Any], Any]:
        cls = type(self)
        field = cls.get_field(name)
        
        if not field:
            raise KeyError(name)

        return field, getattr(self, name)

    def __eq__(self, other: Any) -> bool:
        """
        Compare two models.

        Parameters
        ----------
        other: :class:`~.Model`
            The other model to compare.
        """
        if not isinstance(other, Model):
            return NotImplemented

        return self.json() == other.json()

    @classmethod
    def from_json(cls: Type[ModelT], data: Any) -> ModelT:
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
            raise TypeError('data must be a dict')

        return cls(**data)

    @property
    def fields(self) -> Tuple[Field[Any]]:
        """
        The fields of the model.
        """
        return tuple(self.__fields__)

    @property
    def options(self) -> ModelOptions:
        """
        The options of the model.
        """
        return self.__options__

    def is_json_serializable(self) -> bool:
        """
        Checks if the model is JSON serializable.
        """
        for field in self.fields:
            assert field.name
            value = safe_getattr(self, field.name)

            if isinstance(value, Model):
                if not value.is_json_serializable():
                    return False
            else:
                if not is_json_serializable(value):
                    return False

        return True

    def copy(self) -> 'Model':
        """
        Returns a copy of the model.
        """
        data = self.json()
        return self.from_json(data)

    def json(self, *, include: Iterable[str] = None, exclude: Iterable[str] = None) -> Dict[str, Any]:
        """
        Serializes the model into a JSON object.

        Parameters
        -----------
        include: Tuple[:class:`str`, ...]
            The names of the fields to include. Defaults to all the model's fields.
        exclude: Tuple[:class:`str`, ...]
            The names of the fields to exclude.
        """
        data = {}

        if not self.is_json_serializable():
            raise ObjectNotSerializable(self)

        for field, value in self._iter(include, exclude):
            if isinstance(value, Model):
                value = value.json()

            data[field.name] = value

        return data

    def to_dict(self, *, include: Iterable[str] = None, exclude: Iterable[str] = None) -> Dict[str, Any]:
        """
        Serializes the model into a dictionary.
        The value returned may not be a valid JSON object.

        Parameters
        -----------
        include: Tuple[:class:`str`, ...]
            The names of the fields to include. Defaults to all the model's fields.
        exclude: Tuple[:class:`str`, ...]
            The names of the fields to exclude.
        """
        data = {}

        for field, value in self._iter(include, exclude):
            if isinstance(value, Model):
                value = value.to_dict()

            data[field.name] = value

        return data

    def _iter(self, include: Iterable[str] = None, exclude: Iterable[str] = None):
        if include is None:
            include = [field.name for field in self.__fields__ if field.name is not None]

        if exclude is None:
            exclude = []

        include_null = self.options['include_null_fields']
        for field in self.fields:
            assert field.name
            if field.name in exclude or field.name not in include:
                continue

            value = getattr(self, field.name)
            if not include_null and value is None:
                continue

            yield field, value
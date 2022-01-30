from __future__ import annotations

from typing import (
    TYPE_CHECKING, 
    Any, 
    Iterable, 
    List, 
    Mapping, 
    Optional, 
    Tuple, 
    TypeVar, 
    Dict, 
    Union, 
    overload, 
    Iterator
)

if TYPE_CHECKING:
    KT = TypeVar('KT')
    VT = TypeVar('VT')
    _T = TypeVar('_T')


__all__ = (
    'ImmutableDict',
    'CaseInsensitiveDict',
    'MultiDict',
    'ImmutableMultiDict',
    'CaseInsensitiveMultiDict',
)

def _append_to_multidict(multidict: MultiDict[Any, Any], key: Any, value: Any) -> None:
    if not isinstance(multidict, ImmutableMultiDict):
        key = multidict.wrap_key(key)

    values = multidict._dict.setdefault(key, [])
    values.append(value)

    multidict._list.append((key, value))

def _update_multidict(multidict: MultiDict[Any, Any], *args: Any, **kwargs: List[Any]) -> None:
    if args:
        mapping = args[0]
        if isinstance(mapping, Iterable):
            for key, value in mapping:
                _append_to_multidict(multidict, key, value)
        else:
            kwargs.update(mapping)

    for key, values in kwargs.items():
        if isinstance(values, Iterable):
            for value in values:
                _append_to_multidict(multidict, key, value)
        else:
            _append_to_multidict(multidict, key, values)

class ImmutableDict(Dict['KT', 'VT']):
    """
    An immutable :class:`dict` wrapper.
    This object cannot be changed once initialized.
    """
    def _is_immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError('This object is immutable')

    setdefault = update = pop = popitem = clear = __setitem__ = __delitem__ = copy = _is_immutable  # type: ignore

class CaseInsensitiveDict(Dict[str, 'VT']):
    """
    A case-insensitive :class:`dict` wrapper.
    """
    def __setitem__(self, key: str, value: VT) -> None:
        return super().__setitem__(key.casefold(), value)

    def __getitem__(self, key: str) -> VT:
        return super().__getitem__(key.casefold())

    def __delitem__(self, key: str) -> None:
        return super().__delitem__(key.casefold())

    def __contains__(self, key: str) -> bool:
        return super().__contains__(key.casefold())

    @overload
    def get(self, key: str) -> Optional[VT]:
        ...
    @overload
    def get(self, key: str, default: Union[VT, _T]) -> Union[VT, _T]:
        ...
    def get(self, key: str, default: Any = None) -> Any:
        return super().get(key.casefold(), default)

    @overload
    def pop(self, key: str) -> VT:
        ...
    @overload
    def pop(self, key: str, default: Union[VT, _T]) -> Union[VT, _T]:
        ...
    def pop(self, key: str, default: Any = None) -> Any:
        return super().pop(key.casefold(), default)


class MultiDict(Mapping['KT', 'VT']):
    """
    A :class:`dict` wrapper that allows multiple values for the same key.

    Example
    -------

    .. code-block:: python

        multidict = MultiDict()

        multidict['foo'] = 'bar'
        multidict['foo'] = 'baz'

        print(multidict['foo']) # ['bar', 'baz']

        value = multidict.getone('foo')
        print(value) # 'bar'

        values = multidict.get('foo')
        print(values) # ['bar', 'baz']

        value = multidict.popone('foo') # multidict.pop('foo') would return ['bar', 'baz']
        print(value) # 'bar'

        print(multidict['foo']) # ['baz']

    """
    if TYPE_CHECKING:
        @overload
        def get(self, key: KT) -> Optional[List[VT]]: # type: ignore
            ...
        @overload
        def get(self, key: KT, default: Union[List[VT], _T]) -> Union[List[VT], _T]:
            ...

    @overload
    def __init__(self) -> None:
        ...
    @overload
    def __init__(self, mapping: Mapping[KT, VT], **kwargs: VT) -> None:
        ...
    @overload
    def __init__(self, mapping: Iterable[Tuple[KT, VT]], **kwargs: VT) -> None:
        ...
    @overload
    def __init__(self, **mapping: VT) -> None:
        ...
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._dict: Dict[KT, List[VT]] = {}
        self._list: List[Tuple[KT, VT]] = []

        _update_multidict(self, *args, **kwargs)

    def __repr__(self) -> str:
        return self._dict.__repr__()

    def __setitem__(self, key: KT, value: VT) -> None:
        """
        Sets a value for a key.
        If the key already exists, the value will be appended to the list.

        Parameters
        ----------
        key: Any
            The key to set.
        value: Any
            The value to set.
        """
        self.set(key, value)

    def __getitem__(self, key: KT) -> List[VT]:
        """
        Gets all the values for a key.

        Parameters
        ----------
        key: Any
            The key to get.

        Raises
        ------
        KeyError
            If the key does not exist.
        """
        key = self.wrap_key(key)
        return self._dict[key]

    def __delitem__(self, key: KT) -> None:
        """
        Deletes all the values for a key.

        Parameters
        ----------
        key: Any
            The key to delete.

        Raises
        ------
        KeyError
            If the key does not exist.
        """
        key = self.wrap_key(key)
        values = self._dict.pop(key)

        for value in values:
            self._list.remove((key, value))

    def __contains__(self, key: KT) -> bool:
        """
        Checks if a key exists.

        Parameters
        ----------
        key: Any
            The key to check.
        """
        if isinstance(self, ImmutableDict):
            return key in self._dict

        return self.wrap_key(key) in self._dict

    def __iter__(self) -> Iterator[KT]:
        """
        Returns an iterator over the keys.
        """
        return iter(self._dict)

    def __len__(self) -> int:
        """
        Returns the number of keys.
        """
        return len(self._dict)

    def __bool__(self) -> bool:
        """
        Returns if the dict is empty.
        """
        return bool(self._dict)

    def wrap_key(self, key: KT) -> KT:
        """
        Wraps a key.
        Subclasses can override this to implement their own custom behaviour, for example to convert a string to a case-insensitive key.

        Parameters
        ----------
        key: Any
            The key to wrap.
        """
        return key

    def set(self, key: KT, *values: VT) -> None:
        """
        Sets a value/values for a key.

        Parameters
        ----------
        key: Any
            The key to set.
        *values: Any
            The values to set.
        """
        key = self.wrap_key(key)
        ret = self._dict.setdefault(key, [])

        ret.extend(values)
        self._list.extend((key, value) for value in values)

    @overload
    def get(self, key: KT) -> Optional[List[VT]]:
        ...
    @overload
    def get(self, key: KT, default: Union[List[VT], _T]) -> Union[List[VT], _T]:
        ...
    def get(self, key: KT, default: Any = None) -> Any:
        """
        Gets all the values for a key.
        If the key does not exist, returns the default value.

        Parameters
        ----------
        key: Any
            The key to get.
        default: Any
            The default value to return.
        """
        key = self.wrap_key(key)
        return self._dict.get(key, default)

    @overload
    def getone(self, key: KT) -> Optional[VT]:
        ...
    @overload
    def getone(self, key: KT, default: Union[VT, _T]) -> Union[VT, _T]:
        ...
    def getone(self, key: KT, default: Any = None) -> Any:
        """
        Gets the first value for a key.
        If the key does not exist, returns the default value.

        Parameters
        ----------
        key: Any
            The key to get.
        default: Any
            The default value to return.
        """
        values = self.get(self.wrap_key(key))
        if not values:
            return default

        return values[0]

    @overload
    def pop(self, key: KT) -> List[VT]:
        ...
    @overload
    def pop(self, key: KT, default: Union[VT, _T]) -> Union[VT, _T]:
        ...
    def pop(self, key: KT, default: Any = None) -> Any:
        """
        Pops all the values for a key.
        If the key does not exist, returns the default value.

        Parameters
        ----------
        key: Any
            The key to pop.
        default: Any
            The default value to return.
        """
        key = self.wrap_key(key)
        value = self._dict.pop(key, default)

        if value is default:
            return value

        self._list = [(k, v) for k, v in self._list if k != key]
        return value
    
    @overload
    def popone(self, key: KT) -> VT:
        ...
    @overload
    def popone(self, key: KT, default: Union[VT, _T]) -> Union[VT, _T]:
        ...
    def popone(self, key: KT, default: Any = None) -> Any:
        """
        Pops the first value for a key.
        If the key does not exist, returns the default value.

        Parameters
        ----------
        key: Any
            The key to pop.
        default: Any
            The default value to return.
        """
        key = self.wrap_key(key)
        values = self.get(key)

        if not values:
            return default

        value = values.pop(0)
        self._list.remove((key, value))
    
        return value

    def setdefault(self, key: KT, default: VT) -> List[VT]:
        """
        Sets a value for a key.
        If the key already exists, its values are returned. Otherwise, the default value is returned and appended to the dict.

        Parameters
        ----------
        key: Any
            The key to set.
        default: Any
            The default value to set.
        """
        key = self.wrap_key(key)
        values = self._dict.get(key)

        if values is None:
            self.set(key, default)

        assert values is not None, 'values is None, but should not be' 
        return values

    @overload
    def update(self, mapping: Mapping[KT, Union[VT, List[VT]]], **kwargs: List[VT]) -> None:
        ...
    @overload
    def update(self, mapping: Iterable[Tuple[KT, VT]], **kwargs: List[VT]) -> None:
        ...
    @overload
    def update(self, **kwargs: List[VT]) -> None:
        ...
    def update(self, *args: Any, **kwargs: Any) -> None:
        """
        Updates the dict with the given mapping/iterable or keyword arguments.
        """
        if args:
            m = args[0]
            if isinstance(m, Iterable):
                for key, value in m:
                    self[key] = value
            else:
                kwargs.update(m)

        for key, value in kwargs.items():
            self[key] = value # type: ignore


class CaseInsensitiveMultiDict(MultiDict[str, 'VT']):
    """
    A case-insensitive multi-dict.
    """
    def wrap_key(self, key: str) -> str:
        return key.casefold()

class ImmutableMultiDict(MultiDict['KT', 'VT']):
    """
    An immutable multi-dict.
    """
    def wrap_key(self, key: KT) -> KT:
        raise TypeError('This object is immutable')

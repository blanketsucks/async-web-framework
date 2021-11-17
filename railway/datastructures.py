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
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union, overload
from urllib.parse import parse_qsl, urlsplit

from . import utils

__all__ = (
    'ImmutableMapping',
    'MultiDict',
    'URL',
)

KT = TypeVar('KT')
VT = TypeVar('VT')
T = TypeVar('T')

def is_immutable(self, *args):
    raise TypeError(f'{self.__class__.__name__!r} is immutable')

class ImmutableMapping(Dict[KT, VT]):
    """
    A :class:`dict` that cannot be modified once initialized.
    """
    setdeafult = update = pop = popitem = clear = __setitem__ = __delitem__ = copy = is_immutable # type: ignore

class MultiDict(Dict[KT, VT]):
    """
    A dictionary that supports multiple values for a single key.
    """
    def __init__(self, *args: Any, **kwargs: Any):
        self._dict: Dict[KT, List[VT]] = {}
        self._list: List[Tuple[KT, VT]] = []

        self.update(*args, **kwargs)

    def __repr__(self) -> str:
        return self._dict.__repr__()

    def __getitem__(self, key: KT) -> VT:
        value = self._dict[key]
        return value[0]

    def __setitem__(self, key: KT, value: VT) -> None:
        self._dict.setdefault(key, []).append(value)
        self._list.append((key, value))

    def __delitem__(self, key: KT) -> None:
        self._dict.__delitem__(key)
        self._list = [(k, v) for k, v in self._list if k != key]

    @utils.clear_docstring
    def clear(self) -> None:
        self._dict = {}
        self._list = []

    @overload
    def get(self, key: KT) -> VT: ...
    @overload
    def get(self, key: KT, default: None) -> Optional[VT]: ...
    @overload
    def get(self, key: KT, default: T) -> Union[VT, T]: ...
    def get(self, key: KT, default: Any=None) -> Optional[VT]: # type: ignore
        """
        Gets the first value belonging to a key.

        Parameters
        ----------
        key: Any
            The key to get the first value for.
        """
        values = self.getall(key)
        if not values:
            return default

        return values[0]

    def getall(self, key: KT) -> List[VT]:
        """
        Gets all the values belonging to a key.

        Parameters
        ----------
        key: Any
            The key to get all values for.
        """
        return self._dict.get(key, [])
    
    @overload
    def pop(self, key: KT) -> VT: ...
    @overload
    def pop(self, key: KT, default: None) -> Optional[VT]: ...
    @overload
    def pop(self, key: KT, default: T) -> Union[VT, T]: ...
    def pop(self, key: KT, default: Any=None) -> Optional[VT]:
        """
        Pops the first value belonging to a key.

        Parameters
        ----------
        key: Any
            The key to pop the first value for.
        default: Any
            The value to return if the key is not found.

        Returns
        -------
        Any
            The value that was popped.
        """
        values = self.getall(key)
        if not values:
            return default

        value = values.pop(0)
        self._list.remove((key, value))

        return value

    @overload
    def popall(self, key: KT) -> List[VT]: ...
    @overload
    def popall(self, key: KT, default: None) -> Optional[List[VT]]: ...
    @overload
    def popall(self, key: KT, default: T) -> Union[List[VT], T]: ...
    def popall(self, key: KT, default: Any=None) -> Optional[List[VT]]: # type: ignore
        """
        Pops all values belonging to a key.

        Parameters
        ----------
        key: Any
            The key to pop all values for.
        """
        values = self.getall(key)
        if not values:
            return default

        del self[key]
        return values

    def items(self):
        return self._list

    def update(self, *args: Any, **kwargs: Any) -> None:
        """
        Updates the dictionary with the given key-value pairs.
        """
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

class Headers(MultiDict[str, str]):
    
    @property
    def content_type(self) -> Optional[str]:
        return self.get('Content-Type')

    @property
    def content_lenght(self) -> Optional[int]:
        lenght = self.get('Content-Length')
        if lenght:
            return int(lenght)

        return None

    @property
    def charset(self) -> Optional[str]:
        content_type = self.content_type
        if content_type:
            return utils.get_charset(content_type)

        return None

    @property
    def user_agent(self) -> Optional[str]:
        return self.get('User-Agent')

    @property
    def host(self) -> Optional[str]:
        return self.get('Host')
        

_T = TypeVar('_T', str, bytes)

class URL(Generic[_T]):
    """
    Parameters
    ----------
    url: Union[:class:`str`, :class:`bytes`]
        The URL to parse.

    Attributes
    -----------
    value: :class:`str`
        The originally passed in URL.
    """
    def __init__(self, url: _T) -> None:
        self.value = url
        self.components = urlsplit(url) # type: ignore

    def __str__(self) -> str:
        return self.value.decode() if isinstance(self.value, bytes) else self.value

    def __repr__(self) -> str:
        return f'<URL scheme={self.scheme!r} hostname={self.hostname!r} path={self.path!r}>'

    def is_bytes(self) -> bool:
        return isinstance(self.value, bytes)

    @property
    def scheme(self) -> _T:
        """
        The scheme of the URL.
        """
        return self.components.scheme
    
    @property
    def netloc(self) -> _T:
        """
        The netloc of the URL.
        """
        return self.components.netloc

    @property
    def path(self) -> _T:
        """
        The path of the URL.
        """
        return self.components.path

    @property
    def hostname(self) -> Optional[_T]:
        """
        The hostname of the URL.
        """
        return self.components.hostname

    @property
    def query(self) -> ImmutableMapping[_T, _T]:
        """
        The query parameters of the URL as an immutable dict.
        """
        ret = self.components.query
        query = parse_qsl(ret) # type: ignore

        return ImmutableMapping(query)

    @property
    def fragment(self) -> Optional[_T]:
        """
        The fragment of the URL.
        """
        return self.components.fragment

    @property
    def username(self) -> Optional[_T]:
        """
        The username of the URL.
        """
        return self.components.username

    @property
    def password(self) -> Optional[_T]:
        """
        The password of the URL.
        """
        return self.components.password

    @property
    def port(self) -> Optional[int]:
        """
        The port of the URL.
        """
        return self.components.port
    
    def replace(
        self, 
        *, 
        scheme: _T=None, 
        netloc: _T=None, 
        path: _T=None, 
        query: _T=None,
        fragement: _T=None,
    ):
        kwargs = {}
        if scheme:
            kwargs['scheme'] = scheme
        if netloc:
            kwargs['netloc'] = netloc
        if path:
            kwargs['path'] = path
        if query:
            kwargs['query'] = query
        if fragement:
            kwargs['fragement'] = fragement

        components = self.components._replace(**kwargs)

        self.components = components
        self.value = components.geturl()

        return self

    def as_dict(self):
        data = self.components._asdict()

        data['hostname'] = self.hostname
        data['port'] = self.port
        data['username'] = self.username
        data['password'] = self.password
        data['query'] = self.query

        return data

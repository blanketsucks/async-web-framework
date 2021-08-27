from typing import Any, Dict, List, Optional, Tuple, TypeVar, Union
from urllib.parse import urlparse, parse_qsl

__all__ = (
    'ImmutableMapping',
    'Headers',
    'URL',
)

KT = TypeVar('KT')
VT = TypeVar('VT')

def is_immutable(obj: Any):
    raise TypeError(f'{obj.__class__.__name__!r} is immutable')

class ImmutableMapping(Dict[KT, VT]):
    def setdefault(self, key: Any, default: Any=None):
        is_immutable(self)

    def update(self, **kwargs: VT) -> None:
        is_immutable(self)

    def pop(self, key: Any, default: Any=None):
        is_immutable(self)

    def popitem(self) -> Tuple[KT, VT]:
        is_immutable(self)

    def clear(self) -> None:
        is_immutable(self)
    
    def __setitem__(self, key: Any, value: Any) -> None:
        is_immutable(self)

    def __delitem__(self, key: Any) -> None:
        is_immutable(self)

    def __repr__(self):
        return super().__repr__()

    def copy(self):
        return dict(self)

    def __copy__(self):
        return self

class MultiDict(dict[Any, Any]):
    def __init__(self, *args: Any, **kwargs: Any):
        self._dict: Dict[str, List[Any]] = {}
        self._list: List[Tuple[str, str]] = []

        self.update(*args, **kwargs)

    def __getitem__(self, key: str) -> str:
        value = self._dict[key]
        return value[0]

    def __setitem__(self, key: str, value: str) -> None:
        self._dict.setdefault(key, []).append(value)
        self._list.append((key, value))

    def __delitem__(self, key: str) -> None:
        self._dict.__delitem__(key)
        
        self._list = [(k, v) for k, v in self._list if k != key]

    def clear(self) -> None:
        self._dict = {}
        self._list = []

    def getall(self, key: str) -> List[str]:
        return self._dict.get(key, [])

class Headers(MultiDict):
    def __iter__(self):
        return self._list.__iter__()

class URL:
    def __init__(self, url: Union[str, bytes]) -> None:
        if isinstance(url, bytes):
            url = url.decode()

        self.value = url
        self.components = urlparse(url)

    def __add__(self, other: Union[str, 'URL', Any]) -> 'URL':
        if isinstance(other, URL):
            return URL(self.value + other.value)
        
        if isinstance(other, str):
            return URL(self.value + other)

        return NotImplemented

    @property
    def scheme(self) -> str:
        return self.components.scheme
    
    @property
    def netloc(self) -> str:
        return self.components.netloc

    @property
    def path(self) -> str:
        return self.components.path

    @property
    def hostname(self) -> Optional[str]:
        return self.components.hostname

    @property
    def query(self) -> ImmutableMapping[str, str]:
        ret = self.components.query
        query = parse_qsl(ret)

        return ImmutableMapping(query)

    @property
    def fragment(self) -> Optional[str]:
        return self.components.fragment

    @property
    def username(self) -> Optional[str]:
        return self.components.username

    @property
    def password(self) -> Optional[str]:
        return self.components.password

    @property
    def port(self) -> Optional[int]:
        return self.components.port

    def __repr__(self) -> str:
        return f'<URL scheme={self.scheme!r} hostname={self.hostname!r} path={self.path!r}>'
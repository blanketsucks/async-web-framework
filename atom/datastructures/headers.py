import base64
import typing

from .errors import MultipleValuesFound, HeaderNotFound

class BasicAuth:
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def encode(self):
        return _build_basic_auth(self.username, self.password)

def _build_basic_auth(username, password):
    user_pass = f"{username}:{password}"
    credentials = base64.b64encode(user_pass.encode()).decode()
    
    return 'Basic ' + credentials

class CaseInsensitiveDict(typing.Dict[str, typing.Any]):
    def __contains__(self, key: str):
        return super().__contains__(key)

    def __delitem__(self, key: str):
        return super().__delitem__(key)

    def __getitem__(self, key: str):
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        return super().get(key, default)

    def pop(self, key: str, default=None):
        return super().pop(key, default)

    def __setitem__(self, key: str, value: typing.Any):
        super().__setitem__(key, value)


class MultiDict(typing.MutableMapping[str, str]):

    __slots__ = (
        '__dict',
        '__list'
    )

    def __init__(self, 
                *args: typing.Union[typing.Mapping, typing.Iterable, typing.Any], 
                **kwargs: str) -> None:

        self.__dict: typing.Dict[str, typing.List[str]] = {}
        self.__list: typing.List[typing.Tuple[str, str]] = []

        self.update(*args, **kwargs)
    
    @property
    def original(self):
        return self.__dict

    def as_list(self):
        return self.__list

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.__list!r})'

    def __contains__(self, key: str):
        if not isinstance(key, str):
            return False

        return key in self.__dict

    def __setitem__(self, key: str, value: str) -> None:
        default = self.__dict.setdefault(key, [])
        default.append(value)

        self.__list.append((key, value))

    def __getitem__(self, key: str):
        keys = self.getall(key)

        if not keys:
            raise KeyError(key)

        if len(keys) == 1:
            return keys[0]

        raise MultipleValuesFound(key)

    def __delitem__(self, key: str) -> None:
        del self.__dict[key]

    def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.List[str]]]:
        yield from self.__dict.keys()

    def __len__(self) -> int:
        return len(self.__list)

    def get(self, key: str, default=None) -> str:
        keys = self.__dict.get(key, None)
        if not keys:
            return default

        return keys[0]

    def getall(self, key: str) -> typing.List[str]:
        keys = self.__dict.get(key, [])
        return keys

    def items(self, list: bool=...) -> typing.Iterator[typing.Tuple[str, str]]:
        if list:
            yield from self.__list
            return

        yield from self.__dict.items()

    def copy(self):
        cls = self.__class__
        return cls(self.items(list=False))

    def clear(self) -> 'MultiDict':
        self.__list.clear()
        self.__dict.clear()

        return self



class HTTPHeaders(MultiDict):
    def __str__(self) -> str:
        headers = '\r\n'.join(f'{key}: {value}' for key, value in self.as_list()) + '\r\n'
        return headers

    def encode(self):
        return str(self).encode()

    def build_subprotocols(self, subprotocols: typing.Tuple[str]) -> str:
        subs = ', '.join(subprotocols)
        
        self['Sec-Websocket-Subprotocols'] = subs
        return subs

    def parse_subprotocols(self) -> typing.Tuple[str]:
        subprotocols = self.get('Sec-Websocket-Subprotocols', '')
        if not subprotocols:
            return ()

        return tuple(subprotocols.split(', '))


    def build_basic_auth(self, username: str, password: str) -> str:
        auth =  _build_basic_auth(self, username, password)

        self['Authorization'] = auth
        return auth

    def parse_basic_auth(self) -> typing.Tuple[str, str]:
        auth = self.auth
        _, credentials = auth.split(' ', 1)

        if not auth:
            raise HeaderNotFound('Authorization')

        user_pass = base64.b64decode(credentials.encode()).decode()
        username, password = user_pass.split(':', 1)

        return username, password

    def get_encoding(self):
        content = self.content_type
        split = content.split('; ')
        
        if len(split) < 2:
            return 'utf-8'

        return split[1].split('=')[1]

    # Common headers

    @property
    def host(self):
        return self.get('Host')

    @property
    def cookies(self):
        cookies = self.getall('Set-Cookie')
        return [Cookies(cookie).load() for cookie in cookies]

    @property
    def cookie(self):
        return self.get('Cookie')

    @property
    def connection(self):
        return self.get('Connection')

    @property
    def user_agent(self):
        return self.get('User-Agent')

    @property
    def auth(self):
        return self.get('Authorization')

    @property
    def content_type(self):
        return self.get('Content-Type')

    @property
    def charset(self):
        return self.get_encoding()

class Cookie:
    def __init__(self, info: typing.Tuple[str, str]) -> None:
        self.__info = info

    @property
    def value(self):
        return self.__info[1]

    @property
    def name(self):
        return self.__info[0]

    def __repr__(self) -> str:
        return '<Cookie {0.name}={0.value!r}>'.format(self)

class Cookies(MultiDict):
    def __init__(self, header: str, *args, **kwargs) -> None:
        self._header = header

        super().__init__(*args, **kwargs)

    def load(self):
        parts = self._header.split('; ')

        for part in parts:
            items = part.split('=')
            if len(items) < 2:
                continue
            
            name, value = items
            self[name] = Cookie((name, value))

        return self

    def __repr__(self) -> str:
        return f'<Cookies({self.as_list()!r})'
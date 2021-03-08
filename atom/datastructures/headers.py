import base64
import typing

from .errors import MultipleValuesFound

class CaseInsensitiveMultiDict(typing.MutableMapping[str, str]):

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

        return key.casefold() in self.__dict

    def __setitem__(self, key: str, value: str) -> None:
        default = self.__dict.setdefault(key.casefold(), [])
        default.append(value)

        self.__list.append((key.casefold(), value))

    def __getitem__(self, key: str):
        keys = self.getall(key)

        if not keys:
            raise KeyError(key)

        if len(keys) == 1:
            return keys[0]

        raise MultipleValuesFound(key)

    def __delitem__(self, key: str) -> None:
        del self.__dict[key.casefold()]

    def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.List[str]]]:
        yield from self.__dict.keys()

    def __len__(self) -> int:
        return len(self.__list)

    def get(self, key: str, default=None) -> str:
        keys = self.__dict.get(key.casefold(), default)
        return keys[0]

    def getall(self, key: str) -> typing.List[str]:
        keys = self.__dict.get(key.casefold(), [])
        return keys

    def items(self) -> typing.Iterator[typing.Tuple[str, str]]:
        yield from self.__list

class HTTPHeaders(CaseInsensitiveMultiDict):
    def __str__(self) -> str:
        headers = '\r\n'.join(f'{key}: {value}' for key, value in self.as_list())
        return headers

    def encode(self):
        return str(self).encode()

    def clear(self) -> None:
        self.__list.clear()
        self.__dict.clear()

        return self

def get_subprotocols(headers: HTTPHeaders) -> str:
    subprotocols = headers.get('Sec-WebSocket-Protocol')
    return ', '.join(subprotocols)

def get_websocket_key(headers: HTTPHeaders) -> str:
    key = headers.get('Sec-WebSocket-Key')
    return ', '.join(key)

def get_auth(headers: HTTPHeaders, basic: bool=False):
    if basic:
        auth = headers.get('')

def build_auth_basic(username: str, password: str):
    user = f"{username}:{password}"
    credentials = base64.b64encode(user.encode()).decode()

    return "Basic " + credentials
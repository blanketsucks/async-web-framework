import base64
import typing

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

    def __contains__(self, key: str):
        if not isinstance(key, str):
            return False

        return key.casefold() in self.__dict

    def __setitem__(self, key: str, value: str) -> None:
        default = self.__dict.setdefault(key.casefold(), [])
        default.append(value)

        self.__list.append((key.casefold(), value))

    def get(self, key: str, default=None):
        return self.__dict.get(key.casefold(), default)


class HTTPHeaders(CaseInsensitiveMultiDict):

    def __str__(self) -> str:
        headers = '\r\n'.join(f'{key}: {value}' for key, value in self.__list)
        return headers

    def __iter__(self):
        yield from self.items()

    def __len__(self) -> int:
        return len(self.__dict)

    def encode(self):
        return str(self).encode()

    def clear(self) -> None:
        self.__list.clear()
        self.__dict.clear()

        return self

    def get_all(self, key: str):
        return self.get(key, [])

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
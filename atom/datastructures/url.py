import urllib.parse
import typing

from .headers import MultiDict

class URL:
    def __new__(cls, value: typing.Union[str, bytes, 'URL']) -> typing.Any:
        if type(value) is bytes:
            url = value.decode()

        if type(value) is URL:
            url = value._url
        else:
            url = value
        
        self = super().__new__(cls)

        self._components = urllib.parse.urlsplit(url)
        self._url = url

        return self
    
    @property
    def scheme(self) -> str:
        return self._components.scheme

    @property
    def netloc(self) -> str:
        return self._components.netloc

    @property
    def path(self) -> str:
        return self._components.path

    @property
    def query(self) -> MultiDict:
        queries = self._components.query.split('?')
        multidict = MultiDict()

        for query in queries:
            name, value = query.split('=')
            multidict[name] = value

        return multidict

    @property
    def fragment(self) -> str:
        return self._components.fragment

    @property
    def username(self) -> typing.Optional[str]:
        return self._components.username

    @property
    def password(self) -> typing.Optional[str]:
        return self._components.password

    @property
    def hostname(self) -> typing.Optional[str]:
        return self._components.hostname

    @property
    def port(self) -> typing.Optional[int]:
        return self._components.port
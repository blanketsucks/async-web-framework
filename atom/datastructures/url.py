import urllib.parse
import typing

class URL:
    def __init__(self, path: str) -> None:
        
        self.__url = path
        self.__components = urllib.parse.urlsplit(self.__url)
    
    @property
    def scheme(self) -> str:
        return self.__components.scheme

    @property
    def netloc(self) -> str:
        return self.__components.netloc

    @property
    def path(self) -> str:
        return self.__components.path

    @property
    def query(self) -> str:
        return self.__components.query

    @property
    def fragment(self) -> str:
        return self.__components.fragment

    @property
    def username(self) -> typing.Optional[str]:
        return self.__components.username

    @property
    def password(self) -> typing.Optional[str]:
        return self.__components.password

    @property
    def hostname(self) -> typing.Optional[str]:
        return self.__components.hostname

    @property
    def port(self) -> typing.Optional[int]:
        return self.__components.port
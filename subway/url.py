from __future__ import annotations

from urllib.parse import SplitResult, urljoin, urlsplit, parse_qsl, urlencode
from typing import Any, Optional, Dict, Union, overload

from .multidict import MultiDict

__all__ = 'URL',

SCHEMES = {
    'http': 80,
    'https': 443,
    'ws': 80,
    'wss': 443,
}

class URL:
    """
    Parameters
    ----------
    url: :class:`str`
        The URL to parse.

    Attributes
    -----------
    value: :class:`str`
        The originally passed in URL.
    """

    def __init__(self, url: str) -> None:
        self.value = url
        self.components = urlsplit(url)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f'<URL scheme={self.scheme!r} hostname={self.hostname!r} path={self.path!r}>'

    def __add__(self, other: object):
        if not isinstance(other, URL):
            return NotImplemented

        return URL(self.value + other.value)

    def __eq__(self, other: object):
        if not isinstance(other, URL):
            return NotImplemented

        return self.value == other.value

    def __lt__(self, other: object):
        if not isinstance(other, URL):
            return NotImplemented

        return self.value < other.value

    def __le__(self, other: object):
        if not isinstance(other, URL):
            return NotImplemented

        return self.value <= other.value
    
    def __ge__(self, other: object):
        if not isinstance(other, URL):
            return NotImplemented

        return self.value >= other.value

    def __gt__(self, other: object):
        if not isinstance(other, URL):
            return NotImplemented

        return self.value > other.value

    def __truediv__(self, other: object):
        if not isinstance(other, (URL, str)):
            return NotImplemented

        return self.join(other)

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def from_components(cls, components: SplitResult) -> URL:
        self = cls.__new__(cls)

        self.components = components
        self.value = components.geturl()

        return self

    @property
    def scheme(self) -> str:
        """
        The scheme of the URL.
        """
        return self.components.scheme

    @property
    def netloc(self) -> str:
        """
        The netloc of the URL.
        """
        return self.components.netloc

    @property
    def path(self) -> str:
        """
        The path of the URL.
        """
        return self.components.path

    @property
    def hostname(self) -> Optional[str]:
        """
        The hostname of the URL.
        """
        return self.components.hostname

    @property
    def query(self) -> MultiDict[str, str]:
        """
        The query parameters of the URL as an immutable multi-dict.
        """
        ret = self.components.query
        query = parse_qsl(ret)

        return MultiDict(query)

    @property
    def fragment(self) -> Optional[str]:
        """
        The fragment of the URL.
        """
        return self.components.fragment

    @property
    def username(self) -> Optional[str]:
        """
        The username of the URL.
        """
        return self.components.username

    @property
    def password(self) -> Optional[str]:
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

    @property
    def default_port(self) -> Optional[int]:
        """
        The default port of the URL.
        """
        if self.port:
            return self.port

        return SCHEMES.get(self.scheme, None)

    def is_absolute(self) -> bool:
        """
        Returns whether the URL is absolute.
        """
        return self.components.scheme != ''

    def is_relative(self) -> bool:
        """
        Returns whether the URL is relative.
        """
        return not self.is_absolute()

    def replace(
        self,
        *,
        scheme: Optional[str] = None,
        netloc: Optional[str] = None,
        path: Optional[str] = None,
        query: Optional[str] = None,
        fragment: Optional[str] = None,
    ) -> URL:
        """
        Replaces the URL components with the given values.

        Parameters
        ----------
        scheme: Optional[:class:`str`]
            The scheme of the URL.
        netloc: Optional[:class:`str`]
            The netloc of the URL.
        path: Optional[:class:`str`]
            The path of the URL.
        query: Optional[:class:`str`]
            The query of the URL.
        fragment: Optional[:class:`str`]
            The fragment of the URL.
        """
        kwargs = {}
        if scheme is not None:
            kwargs['scheme'] = scheme
        if netloc is not None:
            kwargs['netloc'] = netloc
        if path is not None:
            kwargs['path'] = path
        if query is not None:
            kwargs['query'] = query
        if fragment is not None:
            kwargs['fragment'] = fragment

        components = self.components._replace(**kwargs)
        return self.from_components(components)

    @overload
    def with_query(self, query: Dict[str, Any]) -> URL: ...
    @overload
    def with_query(self, **query: Any) -> URL: ...
    def with_query(self, query: Optional[Dict[str, Any]] = None, **kwargs: Any) -> URL:
        """
        Returns a new URL with the query parameters replaced.

        Parameters
        ----------
        query: :class:`dict`
            The query parameters to replace.
        **kwargs:
            The query parameters to replace.
        """
        if query is None:
            query = {}

        query.update(kwargs)
        return self.replace(query=urlencode(query))

    def with_scheme(self, scheme: str) -> URL:
        """
        Returns a new URL with the scheme replaced.

        Parameters
        ----------
        scheme: :class:`str`
            The scheme to replace.
        """
        if scheme not in SCHEMES:
            raise ValueError(f'Invalid scheme {scheme!r}')

        return self.replace(scheme=scheme)

    def join(self, url: Union[str, URL]) -> URL:
        """
        Joins the URL with another URL.

        Parameters
        ----------
        url: Union[:class:`str`, :class:`!.URL`]
            The URL to join with.
        """
        if isinstance(url, URL):
            url = str(url)

        return URL(urljoin(self.value, url))

    def as_dict(self) -> Dict[str, str]:
        return self.components._asdict()

    def encode(self, *, encoding: Optional[str] = None, errors: Optional[str] = None) -> bytes:
        """
        Encodes the URL as bytes.

        Parameters
        ----------
        encoding: Optional[:class:`str`]
            The encoding to use.
        """
        if not encoding:
            encoding = 'utf-8'

        if not errors:
            errors = 'strict'

        return self.value.encode(encoding, errors)
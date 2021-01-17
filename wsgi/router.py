import functools
from .error import HTTPNotFound, HTTPBadRequest
import re

class Route:
    def __init__(self, path: str, method: str, coro) -> None:
        self._path = path
        self._method = method
        self._coro = coro

    @property
    def path(self):
        return self._path

    @property
    def method(self):
        return self._method

    @property
    def coro(self):
        return self._coro

    def __repr__(self):
        return (self.method, self.path)


class URLRouter:
    _param_regex = r"{(?P<param>\w+)}"

    def __init__(self) -> None:
        self._routes = {}

    def resolve(self, request):
        key = (request.method, request.url.path)

        if key not in self._routes:
            raise HTTPNotFound(reason=f"Could not find {request.url.raw_path!r}")

        if key[0] != request.method:
            raise HTTPBadRequest(reason=f"{request.method!r} is not allowed for {request.url.raw_path!r}")
            
        return self._routes[key]

    def _format_pattern(self, path):
        if not re.match(re.compile(self._param_regex), path):
            return path

        regex = r""
        last_pos = 0

        for match in re.finditer(self._param_regex, path):
            regex += path[last_pos: match.start()]
            param = match.group("param")
            regex += r"(?P<%s>\w+)" % param
            last_pos = match.end()

        return regex

    def add_route(self, route: Route):
        self._routes[(route.method, route.path)] = route.coro

def resolve(self, request):
    for (method, pattern), handler in self._routes.items():
        match = re.match(pattern, request.url.raw_path)

        if match is None:
            raise HTTPNotFound(reason=f"Could not find {request.url.raw_path!r}")

        if method != request.method:
            raise HTTPBadRequest(reason=f"{request.method!r} is not allowed for {request.url.raw_path!r}")

        return match.groupdict(), handler


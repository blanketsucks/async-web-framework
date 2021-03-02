from .errors import NotFound, BadRequest
from .objects import Route, WebsocketRoute

import re
import typing

__all__ = (
    'Router',
)

class Router:
    _param_regex = r"{(?P<param>\w+)}"

    def __init__(self) -> None:
        self.routes: typing.List[typing.Union[Route, WebsocketRoute]] = []

    def resolve(self, request) -> typing.Tuple[typing.Dict, typing.Union[Route, WebsocketRoute]]:
        for route in self.routes:
            match = re.match(route.path, request.url.raw_path)

            if match is None:
                continue

            if match:
                if route.method != request.method:
                    raise BadRequest(reason=f"{request.method!r} is not allowed for {request.url.raw_path!r}")
                

                return match.groupdict(), route
        
        raise NotFound(reason=f'Could not find {request.url.raw_path!r}')

    def _format_pattern(self, path: str):
        if not re.search(self._param_regex, path):
            return path

        regex = r""
        last_pos = 0

        for match in re.finditer(self._param_regex, path):
            regex += path[last_pos: match.start()]
            param = match.group("param")
            regex += r"(?P<%s>\w+)" % param
            last_pos = match.end()

        return regex

    def add_route(self, path: str, method: str, coroutine: typing.Coroutine, *, websocket: bool=False):
        pattern = self._format_pattern(path)
        route = Route(pattern, method, coroutine)

        if websocket:
            route = WebsocketRoute(pattern, method, coroutine)

        self.routes.append(route)
        return route

    


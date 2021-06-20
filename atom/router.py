from .errors import NotFound, BadRequest
from .objects import Route, WebsocketRoute

import re
import typing

if typing.TYPE_CHECKING:
    from .request import Request

__all__ = (
    'Router',
)


class Router:
    _param_regex = r"{(?P<param>\w+)}"

    def __init__(self) -> None:
        self.routes: typing.List[typing.Union[Route, WebsocketRoute]] = []

    def resolve(self, request: 'Request') -> typing.Tuple[typing.Dict, typing.Union[Route, WebsocketRoute]]:
        for route in self.routes:
            match = re.fullmatch(route.path, request.url.path)

            if match is None:
                continue

            if match:
                if route.method != request.method:
                    raise BadRequest(reason=f"{request.method!r} is not allowed for {request.url.path!r}")

                return match.groupdict(), route

        raise NotFound(reason=f'Could not find {request.url.path!r}')

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

    def add_route(self, route: Route, *, websocket: bool = False):
        pattern = self._format_pattern(route.path)
        route.path = pattern

        self.routes.append(route)
        return route

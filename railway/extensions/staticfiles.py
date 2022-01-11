from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List, Optional, Any
from pathlib import Path
import functools
import re

from railway.types import StrPath
from railway import open, FileResponse, Route, utils

if TYPE_CHECKING:
    from ..app import Application

__all__ = 'StaticFiles',

IGNORE_EXTENSION_REGEX = re.compile(r"\*\.([a-zA-Z0-9]+)")


def _make_ignored_extensions(ignored: Iterable[str]) -> List[str]:
    extensions = []
    for filename in ignored:
        match = IGNORE_EXTENSION_REGEX.match(filename)
        if match:
            extensions.append(match.group(1))

    return extensions


class StaticFiles:
    def __init__(self, directory: StrPath, *, ignore: Optional[Iterable[str]] = None) -> None:
        self.directory = Path(directory)
        self.ignore = ignore or []
        self.ignored_extensions = _make_ignored_extensions(self.ignore)

    @staticmethod
    def get_file_extension(filename: str) -> str:
        return filename.split('.')[-1]

    def should_ignore(self, filename: str) -> bool:
        extension = self.get_file_extension(filename)
        return filename in self.ignore or extension in self.ignored_extensions

    async def route(self, filename: str, *_: Any) -> FileResponse:
        path = self.directory / filename
        async with open(path) as f:
            return FileResponse(f)

    def create_route(self, filename: str, app: Application) -> Route:
        callback = functools.partial(self.route, filename)
        callback.__name__ = f"route_{filename}"  # type: ignore

        return app.add_route(callback, f"/{filename}", 'GET', websocket=False)

    def mount(self, app: Application) -> None:
        for entry in utils.listdir(self.directory):
            if self.should_ignore(entry.name):
                continue

            self.create_route(entry.name, app)

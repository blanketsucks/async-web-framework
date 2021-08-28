from typing import Any, Dict, List, Union, overload, Tuple, Optional
import asyncio
import pathlib
import re
import ast

from . import compat
from .response import HTMLResponse

__all__ = ('Template', 'render')

def _wrap(text: str, start: str, end: str):
    return start + text + end

def _is_valid_python(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False

def _include(fn: str):
    with open(fn, 'r') as f:
        return f.read()

@overload
def _iterate(iterable: Union[List[Any], Tuple[Any]], *, key: str, sep: str='\n') -> str: ...
@overload
def _iterate(iterable: Dict[str, Any], *, key: str, value: str, sep: str='\n') -> str: ...
def _iterate(iterable: Union[List[Any], Tuple[Any], Dict[str, Any], Any], **kwargs: str) -> str:
    items: List[str] = []
    sep = kwargs.get('sep', '\n')

    if isinstance(iterable, dict):
        for k, v in iterable.items():
            key = kwargs['key']
            value = kwargs['value']

            key = key.format(key=k)
            value = value.format(value=v)

            items.append(key + sep + value)

    elif isinstance(iterable, (list, tuple)):
        for v in iterable:
            key = kwargs['key']

            key = key.format(key=v)
            items.append(key + sep)

    return ''.join(items)

class Context:
    regex = re.compile(r'(?<={{).+?(?=}})', re.MULTILINE)

    def __init__(self, template: 'Template', kwargs: Dict[str, Any]) -> None:
        self.template = template

        self.variables = {
            'include': _include,
            'iterate': _iterate,
            **kwargs
        }

    def findall(self, text: str):
        matches = self.regex.finditer(text)

        for match in matches:
            yield match.group()

    async def render(self) -> str:
        source = await self.template.read()

        for match in self.findall(source):
            original = match
            match = match.strip(' ')

            wrapped = _wrap(original, r'{{', r'}}')

            if _is_valid_python(match):
                ret = eval(match, self.variables)
                source = source.replace(wrapped, str(ret))

                continue

            source = source.replace(wrapped, str(self.variables[match]))

        return source

class Template:
    def __init__(self, path: Union[str, pathlib.Path, Any], loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        if isinstance(path, str):
            self.path = path
        elif isinstance(path, pathlib.Path):
            self.path = path.name
        else:
            raise TypeError('path must be a string or pathlib.Path')

        self.fp = open(self.path, 'r')
        self.loop = loop or compat.get_event_loop()

    async def read(self) -> str:
        if self.fp.closed:
            raise ValueError('file is closed')

        source = await self.loop.run_in_executor(None, self.fp.read)
        return source

async def render(
    path: str,
    __globals: Optional[Dict[str, Any]]=None, 
    __locals: Optional[Dict[str, Any]]=None, 
    **kwargs: Any
):
    if not __globals:
        __globals = {}

    if not __locals:
        __locals = {}

    loop = asyncio.get_running_loop()
    vars = {**__globals, **__locals, **kwargs}

    template = Template(path, loop)
    context = Context(template, vars)

    body = await context.render()
    template.fp.close()

    response = HTMLResponse(body)
    return response
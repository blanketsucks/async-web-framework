"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Any, Dict, Union, Optional
import asyncio
import pathlib
import re
import ast

from . import compat
from .response import HTMLResponse

__all__ = ('TemplateContext', 'Template', 'render')

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

class TemplateContext:
    """
    Helper for rendering templates.

    Parameters
    -----------
    template: :class:`~railway.templates.Template`
        The template to render.
    \*\*kwargs:
        The variables to pass to the template.
    """
    regex = re.compile(r'(?<={{).+?(?=}})', re.MULTILINE)

    def __init__(self, template: 'Template', kwargs: Dict[str, Any]) -> None:
        self.template = template

        self.variables = {
            'include': _include,
            **kwargs
        }

    def findall(self, text: str):
        matches = self.regex.finditer(text)

        for match in matches:
            yield match.group()

    async def render(self) -> str:
        """
        Renders a template.
        """
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
    """
    A template object used as a helper for rendering HTML.

    Parameters
    -----------
    path: Union[:class:`str`, :class:`pathlib.Path`]
        The path to the template file.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop to use for async operations.

    Attributes
    -----------
    path: Union[:class:`str`, :class:`pathlib.Path`]
        The path to the template file.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop to use for async operations.
    """
    def __init__(self, path: Union[str, pathlib.Path, Any], loop: Optional[asyncio.AbstractEventLoop]=None) -> None:
        if isinstance(path, str):
            self.path: str = path
        elif isinstance(path, pathlib.Path):
            self.path: str = str(path)
        else:
            raise TypeError('path must be a string or pathlib.Path')

        self.fp = open(self.path, 'r')
        self.loop: asyncio.AbstractEventLoop = loop or compat.get_event_loop()

    async def read(self) -> str:
        """
        Reads the template file.
        """
        source = await self.loop.run_in_executor(None, self.fp.read)
        return source

    def close(self) -> None:
        """
        Closes the template file.
        """
        self.fp.close()

async def render(
    path: Union[str, pathlib.Path],
    loop: asyncio.AbstractEventLoop=None,
    __globals: Optional[Dict[str, Any]]=None, 
    __locals: Optional[Dict[str, Any]]=None, 
    **kwargs: Any
) -> HTMLResponse:
    """
    Renders an HTML file.

    Parameters
    -----------
    path: Union[:class:`str`, :class:`pathlib.Path`]
        The path to the template file.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop to use.
    __globals: Optional[:class:`dict`]
        The global variables to use for the template.
    __locals: Optional[:class:`dict`]
        The local variables to use for the template.
    \*\*kwargs: 
        The variables to use for the template.
    """
    if not __globals:
        __globals = {}

    if not __locals:
        __locals = {}

    vars = {**__globals, **__locals, **kwargs}

    template = Template(path, loop)
    context = TemplateContext(template, vars)

    body = await context.render()
    template.close()

    response = HTMLResponse(body)
    return response
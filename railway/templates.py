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
import pathlib
import jinja2

from .response import HTMLResponse

__all__ = ('render', 'create_default_jinja2_env')

def create_default_jinja2_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('.'),
        enable_async=True,
    )
    
    return env

environment = create_default_jinja2_env()

async def render(
    path: Union[str, pathlib.Path],
    env: jinja2.Environment=None,
    globals: Optional[Dict[str, Any]]=None, 
    locals: Optional[Dict[str, Any]]=None, 
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
    **kwargs: 
        The variables to use for the template.
    """
    env = env or environment

    if not env.is_async:
        raise TypeError('The jinja2 env passed in must have async enabled')

    if not globals:
        globals = {}

    if not locals:
        locals = {}

    vars = {**globals, **locals, **kwargs}

    template = env.get_template(str(path))
    body = await template.render_async(**vars)

    response = HTMLResponse(body)
    return response

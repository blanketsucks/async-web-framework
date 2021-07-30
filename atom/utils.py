import traceback
import markdown as mark
import json
import traceback
import warnings
import functools
from typing import Type, Generator, Tuple

from .response import Response, HTMLResponse, JSONResponse

__all__ = (
    'format_exception',
    'jsonify',
    'markdown',
    'render_html',
    'deprecated',
    'Deprecated',
    'SETTING_ENV_PREFIX',
    'VALID_METHODS'
)

class Deprecated:
    def __init__(self, func) -> None:
        self.__repr = '<Deprecated name={0.__name__!r}>'.format(func)

    def __bool__(self):
        return False

    def __repr__(self) -> str:
        return self.__repr


SETTING_ENV_PREFIX = 'ATOM_'

VALID_METHODS = (
    "GET",
    "POST",
    "PUT",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "DELETE"
)

def warn(message: str, category: Type[Warning]):
    warnings.simplefilter('always', category)
    warnings.warn(message, category, stacklevel=4)

    warnings.simplefilter('default', category)

def deprecated(other=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Deprecated:
            if other:
                warning = f'{func.__name__} is deprecated, use {other} instead.'
            else:
                warning = f'{func.__name__} is deprecated.'

            warn(warning, DeprecationWarning)
            return Deprecated(func)
        return wrapper
    return decorator


def format_exception(exc):
    server_exception_templ = """
    <div>
        <h1>500 Internal server error</h1>
        <span>Server got itself in trouble : <b>{exc}</b><span>
        <p>{traceback}</p>
    </div> 
    """

    resp = Response(status=500, content_type="text/html")
    trace = traceback.format_exc().replace("\n", "</br>")

    msg = server_exception_templ.format(exc=str(exc), traceback=trace)
    resp.add_body(msg)

    return resp


def jsonify(*, response=True, **kwargs):
    """Inspired by Flask's jsonify"""
    data = json.dumps(kwargs, indent=4)

    if response:
        resp = JSONResponse(data)
        return resp

    return data

def markdown(fp: str):
    actual = fp + '.md'

    with open(actual, 'r') as file:
        content = file.read()
        resp = mark.markdown(content)

        return HTMLResponse(resp)


def render_html(fp: str):
    actual = fp + '.html'

    with open(actual, 'r') as file:
        resp = file.read()
        return HTMLResponse(resp)

def iter_headers(headers: bytes) -> Generator:
    offset = 0

    while True:
        index = headers.index(b'\r\n', offset) + 2
        data = headers[offset:index]
        offset = index

        if data == b'\r\n':
            return

        yield [item.strip().decode() for item in data.split(b':', 1)]

def find_headers(data: bytes) -> Tuple[Generator, str]:
    while True:
        end = data.find(b'\r\n\r\n') + 4

        if end != -1:
            headers = data[:end]
            body = data[end:]

            return iter_headers(headers), body
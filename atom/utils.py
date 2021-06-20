import traceback
from .response import Response, HTMLResponse, JSONResponse
import markdown as mark
import codecs
import json
import traceback
import warnings
import functools
import typing
import humanize
import aiohttp

__all__ = (
    'format_exception',
    'jsonify',
    'markdown',
    'render_html',
    'deprecated',
    'Deprecated',
    'DEFAULT_SETTINGS',
    'VALID_SETTINGS',
    'SETTING_ENV_PREFIX',
    'VALID_LISTENERS',
    'VALID_METHODS'
)


class Deprecated:
    def __init__(self, func) -> None:
        self.__repr = '<Deprecated name={0.__name__!r}>'.format(func)

    def __bool__(self):
        return False

    def __repr__(self) -> str:
        return self.__repr


DEFAULT_SETTINGS = {
    'HOST': 'http://127.0.0.1/',
    'PORT': 8080,
    'DEBUG': False,
    'SECRET_KEY': None
}

VALID_SETTINGS: typing.Tuple = (
    'SECRET_KEY',
    'DEBUG',
    'PORT',
    'HOST'
)
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

VALID_LISTENERS: typing.Tuple = (
    'on_startup',
    'on_shutdown',
    'on_error',
    'on_connection_made',
    'on_connection_lost',
    'on_data_receive',
    'on_data_sent',
)


def deprecated(other=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Deprecated:
            warnings.simplefilter('always', DeprecationWarning)

            if other:
                warning = f'{func.__name__} is deprecated, use {other} instead.'
            else:
                warning = f'{func.__name__} is deprecated.'

            warnings.warn(warning, DeprecationWarning, stacklevel=3)
            warnings.simplefilter('default', DeprecationWarning)

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

def iter_headers(headers: bytes) -> typing.Generator:
    offset = 0

    while True:
        index = headers.index(b'\r\n', offset) + 2
        data = headers[offset:index]
        offset = index

        if data == b'\r\n':
            return

        yield [item.strip().decode() for item in data.split(b':', 1)]

def find_headers(data: bytes) -> typing.Tuple[typing.Generator, str]:
    while True:
        end = data.find(b'\r\n\r\n') + 4

        if end != -1:
            headers = data[:end]
            body = data[end:]

            return iter_headers(headers), body
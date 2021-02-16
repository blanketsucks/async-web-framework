import traceback
from .response import Response, HTMLResponse, JSONResponse
import markdown as mark
import codecs
import json
import traceback
import warnings
import functools
import typing


__all__ = (
    'format_exception',
    'jsonify',
    'markdown',
    'render_html',
    'deprecated',
    'DEFAULT_SETTINGS',
    'VALID_SETTINGS',
    'SETTING_ENV_PREFIX',
    'VALID_LISTENERS'
)

DEFAULT_SETTINGS = {
    'HOST': '127.0.0.1',
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

VALID_LISTENERS: typing.Tuple = (
    'on_startup',
    'on_shutdown',
    'on_connection_made',
    'on_connection_lost',
    'on_socket_receive',
    'on_database_connect',
    'on_database_close',
    'on_request'
)

def deprecated(other=None):
    def wrapper(func):
        warnings.simplefilter('always', DeprecationWarning)

        if other:
            warning = f'{func.__name__} is deprecated, use {other} instead.'
        else:
            warning = f'{func.__name__} is deprecated.'

        warnings.warn(warning, DeprecationWarning, stacklevel=3)
        warnings.simplefilter('default', DeprecationWarning)

        return func
    return wrapper

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

    with codecs.open(actual, 'r') as file:
        resp = file.read()
        return HTMLResponse(resp)


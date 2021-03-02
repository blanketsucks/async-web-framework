import typing
from bs4 import BeautifulSoup
import urllib.parse
from .request import Request
from .response import HTMLResponse, JSONResponse, Response
from . import utils

if typing.TYPE_CHECKING:
    from .app import Application
    from .restful import RESTApplication

__all__ = (
    'Context',
)

class _ContextManager:
    def __init__(self, context) -> None:
        self.__context = context

    def __enter__(self):
        return self.__context

    def __exit__(self, _type, value, tb):
        del self.__context
        return self

class _RedirectContextManager:
    def __init__(self, 
                to: str, 
                headers: typing.Dict=None, 
                status: int=302, 
                content_type: str='text/html', 
                *, 
                context: 'Context') -> None:
        self._url = to

        self.headers = headers
        self.status = status
        self.context_type = content_type

        self.__ctx = context
        self.__response = None

    def __enter__(self):
        self.headers['Location'] = self._url
        
        self.__response = response = Response(
            status=self.status,
            content_type=self.context_type,
            headers=self.headers
        )

        self.__ctx.response = response
        return response

    def __exit__(self, _type, value, tb):
        del self.__response
        return self

class Context:
    def __init__(self, 
                *, 
                app: typing.Union['Application', 'RESTApplication'], 
                request: Request) -> None:

        self._app = app
        self._request = request

        self.__response = None

    @property
    def app(self):
        return self._app
    
    @property
    def request(self):
        return self._request

    @property
    def response(self):
        return self.__response

    @response.setter
    def response(self, value):
        if not isinstance(value, (Response, HTMLResponse, JSONResponse)):
            fmt = 'Expected Response, HTMLResponse or JSONResponse but got {0.__class__.__name__} instead'
            raise ValueError(fmt.format(value))

        self.__response = value

    def __repr__(self) -> str:
        return '<Context response={0.response} request={0.request} app={0.app}>'.format(self)

    def build_html_response(self, 
                            body: str, *, 
                            status: int=None, 
                            headers: typing.Dict=None):
        if not isinstance(body, str):
            raise ValueError('Expected str but got {0.__class__.__name__} instead'.format(body))

        self.__response = response = HTMLResponse(body, status, headers)
        return response

    def build_json_response(self, 
                            body: typing.Union[typing.Dict, typing.List],
                            *,
                            status: int=200,
                            headers: typing.Dict=None):
        if not isinstance(body, dict):
            raise ValueError('Expected dict but got {0.__class__.__name__} instead'.format(body))

        response = utils.jsonify(response=True, **body)
        if headers:
            response._headers.update(headers)

        response._status = status
        self.__response = response
        
        return response

    def build_response(self, body: typing.Union[str, typing.List, typing.Dict, typing.Any], **kwargs):
        if isinstance(body, str):
            parser = BeautifulSoup(body, features='html.parser')

            if bool(parser.find()):
                return self.build_html_response(body, **kwargs)

            self.__response = response = Response(body, **kwargs)
            return response

        if isinstance(body, (dict, list)):
            return self.build_json_response(body, **kwargs)
        
        self.__response = response = Response(body, **kwargs)
        return response
         
    def redirect(self, to: str, headers: typing.Dict=None, status: int=302, content_type: str='text/html'):
        headers = headers or {}

        url = urllib.parse.quote_plus(to, ":/%#?&=@[]!$&'()*+,;")
        headers['Location'] = url

        self.__response = response = Response(
            status=status,
            content_type=content_type,
            headers=headers
        )
        return response
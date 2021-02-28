import typing
from bs4 import BeautifulSoup

from .request import Request
from .response import HTMLResponse, JSONResponse, Response

if typing.TYPE_CHECKING:
    from .app import Application
    from .restful import RESTApplication

__all__ = (
    'Context'
)

class _ContextManager:
    def __init__(self, context) -> None:
        self.__context = context

    def __enter__(self):
        return self.__context

    def __exit__(self):
        del self.__context
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
                            status: int=None, 
                            headers: typing.Dict=None):
        if not isinstance(body, (dict, list)):
            raise ValueError('Expected dict or list but got {0.__class__.__name__} instead'.format(body))

        self.__response = response = JSONResponse(body, status, headers)
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
         
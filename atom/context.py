import typing
import urllib.parse
from .request import Request
from .response import HTMLResponse, JSONResponse, Response
from . import utils

if typing.TYPE_CHECKING:
    from .app import Application

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


class Context:
    def __init__(self,
                 *,
                 app: 'Application',
                 request: Request,
                 args: typing.Tuple) -> None:

        self.app = app
        self.request = request
        self.args = args

        self.__response = None

    @property
    def status(self):
        return self.request.status_code

    @property
    def route(self):
        return self.request.route

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
                            status: int = None,
                            headers: typing.Dict = None):
        if not isinstance(body, str):
            raise ValueError('Expected str but got {0.__class__.__name__} instead'.format(body))

        self.__response = response = HTMLResponse(body, status, headers)
        return response

    def build_json_response(self,
                            body: typing.Union[typing.Dict, typing.List],
                            *,
                            status: int = 200,
                            headers: typing.Dict = None):
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
            return self.build_html_response(body, **kwargs)

        if isinstance(body, (dict, list)):
            return self.build_json_response(body, **kwargs)

        self.__response = response = Response(body, **kwargs)
        return response

    async def redirect(self, to: str, headers: typing.Dict = None, status: int = 302, content_type: str = 'text/html'):
        headers = headers or {}

        url = urllib.parse.quote_plus(to, ":/%#?&=@[]!$&'()*+,;")
        headers['Location'] = url

        self.__response = response = Response(
            status=status,
            content_type=content_type,
            headers=headers
        )
        return response

import json
import typing
import yarl

class Request:
    _encoding = "utf-8"

    def __init__(self, method: bytes, url: bytes, status_code,
                headers: typing.Dict[str, typing.Any], version=None, body=None):

        self._version = version
        self._status_code = status_code
        
        self._method = method.decode(self._encoding)
        self._url = yarl.URL(url.decode(self._encoding))

        self._headers = headers
        self._body = body

        self._args: typing.Dict[str, typing.Any] = {}

    @property
    def method(self):
        return self._method

    @property
    def url(self):
        return self._url

    @property
    def headers(self):
        return self._headers

    @property
    def status(self):
        return self._status_code

    @property
    def params(self):
        return self._url.query

    @property
    def args(self):
        return self._args

    def text(self):
        if self._body is not None:
            return self._body.decode(self._encoding)

    def json(self, **kwargs):
        text = self.text()
        if text is not None:
            return json.loads(text, **kwargs)
    
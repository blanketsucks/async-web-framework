import json
import typing
import yarl

class Request:
    _encoding = "utf_8"

    def __init__(self, method, url, status_code, headers, version=None, body=None, app=None):
        self._version = version
        self._status_code = status_code
        
        self._method = method.decode(self._encoding)
        self._url = yarl.URL(url.decode(self._encoding))

        self._headers: typing.Dict[str, typing.Any] = headers
        self._body = body

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
    def args(self):
        return self._url.query

    def text(self):
        if self._body is not None:
            return self._body.decode(self._encoding)

    def json(self, **kwargs):
        text = self.text()
        if text is not None:
            return json.loads(text, **kwargs)
    
import http.server
import typing
import urllib.parse

responses = http.server.BaseHTTPRequestHandler.responses

__all__ = (
    'Response',
    'HTMLResponse',
    'JSONResponse',
    'redirect'
)

class Response:
    def __init__(self, body='',
                status=200, content_type="text/plain",
                headers=None, version="1.1"):

        self.version = version
        self._status = status
        self._body = body
        self._content_type = content_type
        self._encoding = "utf-8"

        if headers is None:
            headers = {}
        
        self._headers = headers
        

    @property
    def body(self):
        return self._body

    @property
    def status(self):
        return self._status

    @property
    def content_type(self):
        return self._content_type

    @property
    def headers(self):
        return self._headers
    
    def add_body(self, data):
        self._body = data

    def add_header(self, key, value):
        self._headers[key] = value

    def __repr__(self) -> str:
        return '<Response body={0.body!r} content_type={0.content_type!r} status={0.status} version={0.version}>'.format(self)
    
    def as_string(self):
        status_msg, _ = responses.get(int(self._status))
        
        messages = [
            f"HTTP/{self.version} {self._status} {status_msg}",
            f"Content-Type: {self._content_type}",
            f"Content-Length: {len(self._body)}",
        ]

        if self.headers:
            for header, value in self.headers.items():
                messages.append(f"{header}: {value}")

        if self._body is not None:
            messages.append("\r\n" + self._body)

        return "\r\n".join(messages)

class HTMLResponse(Response):
    def __init__(self, body='', status=200, headers=None, version='1.1'):
        super().__init__(body=body, status=status, content_type='text/html', headers=headers, version=version)

class JSONResponse(Response):
    def __init__(self, body='', status=200, headers=None, version='1.1'):
        super().__init__(body=body, status=status, content_type='application/json', headers=headers, version=version)

def redirect(to: str, headers: typing.Dict=None, status: int=302, content_type: str='text/html'):
    headers = headers or {}

    url = urllib.parse.quote_plus(to, ":/%#?&=@[]!$&'()*+,;")
    headers['Location'] = url

    return Response(
        status=status,
        headers=headers,
        content_type=content_type
    )

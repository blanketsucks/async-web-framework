from typing import Any
from . import http
from .app import Application

__all__ = (
    'TestClient',
)

class TestClient:
    def __init__(self, app: Application) -> None:
        self.app = app
        self.session = http.HTTPSession()

    @property
    def host(self):
        return self.app.host

    @property
    def port(self):
        return self.app.port

    def ws_connect(self, path: str):
        url = self.app.url_for(path, is_websocket=True)
        return self.session.ws_connect(url)

    def request(self, path: str, method: str, **kwargs: Any):
        url = self.app.url_for(path)
        return self.session.request(url=url, method=method, **kwargs)

    def get(self, path: str, **kwargs: Any):
        return self.request(path, 'GET', **kwargs)

    def post(self, path: str, **kwargs: Any):
        return self.request(path, 'POST', **kwargs)

    def put(self, path: str, **kwargs: Any):
        return self.request(path, 'PUT', **kwargs)

    def delete(self, path: str, **kwargs: Any):
        return self.request(path, 'DELETE', **kwargs)


    
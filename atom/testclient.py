from . import http
from .app import Application

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
        url = f'ws://{self.host}:{self.port}{path}'
        return self.session.ws_connect(url)

    def request(self, path: str, method: str, **kwargs):
        url = f'http://{self.host}:{self.port}{path}'
        return self.session.request(url=url, method=method, **kwargs)

    def get(self, path: str, **kwargs):
        return self.request(path, 'GET', **kwargs)

    def post(self, path: str, **kwargs):
        return self.request(path, 'POST', **kwargs)

    def put(self, path: str, **kwargs):
        return self.request(path, 'PUT', **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request(path, 'DELETE', **kwargs)


    
from typing import Any

from .http import HTTPSession
from .app import Application

__all__ = (
    'TestClient',
)


class TestClient:
    """
    Test client for the application.

    Attributes
    ----------
    app: :class:`~.Application`
        The application to test.
    session: :class:`~.http.HTTPSession`
        The HTTP session used.
    """

    def __init__(self, app: Application) -> None:
        self.app: Application = app
        self.session = HTTPSession()

    async def __aenter__(self):
        if not self.app.is_serving():
            await self.app.start()

        return self

    async def __aexit__(self, *args):
        if self.app.is_serving():
            await self.app.close()

        await self.session.close()

    @property
    def host(self) -> str:
        return self.app.host

    @property
    def port(self) -> int:
        return self.app.port

    def ws_connect(self, path: str):
        """
        Performs a websocket connection.

        Parameters
        -------------
        path: :class:`str`
            The path to the websocket resource.

        Example
        ---------
        .. code-block:: python3

            import subway
            from subway import websockets

            app = subway.Application()
            client = subway.TestClient(app)

            @app.websocket('/ws')
            async def handler(request: subway.Request, ws: websockets.ServerWebSocket):
                await ws.send(b'Hello!')

                data = await ws.receive()
                print(data.data)

                await ws.close()

            async def main():
                async with client:
                    async with client.ws_connect('/ws') as ws:
                        message = await ws.receive_str()
                        print(message)

                        await ws.send(b'Hi!')
            
            app.loop.run_until_complete(main())
            ```
        """
        url = self.app.url_for(path, is_websocket=True)
        return self.session.ws_connect(str(url))

    def request(self, path: str, method: str, **kwargs: Any):
        """
        Sends a request to the application.

        Parameters
        ----------
        path: :class:`str`
            The path to the resource.
        method: :class:`str`
            The HTTP method to use.
        **kwargs: Any
            The keyword arguments to pass to the request.

        Example
        ---------

        .. code-block:: python3

            import subway

            app = subway.Application()

            @app.route('/')
            async def index(request: subway.Request):
                return 'another creative response'

            async def main():
                async with subway.TestClient(app) as client:
                    async with client.get('/') as response:
                        print(response.status)
                        text = await response.text()

                        print(text)

            app.loop.run_until_complete(main())
            
        """
        url = self.app.url_for(path)
        return self.session.request(url=str(url), method=method, **kwargs)

    def get(self, path: str, **kwargs: Any):
        return self.request(path, 'GET', **kwargs)

    def post(self, path: str, **kwargs: Any):
        return self.request(path, 'POST', **kwargs)

    def put(self, path: str, **kwargs: Any):
        return self.request(path, 'PUT', **kwargs)

    def delete(self, path: str, **kwargs: Any):
        return self.request(path, 'DELETE', **kwargs)

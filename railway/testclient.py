"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from typing import Any, Optional
from . import http
from .app import Application

__all__ = (
    'TestClient',
)

class TestClient:
    """
    Test client for the application.

    Attributes
    ----------
    app: 
        The application to test.
    session: 
        The HTTP session used.
    """
    def __init__(self, app: Application) -> None:
        self.app: Application = app
        self.session: http.HTTPSession = http.HTTPSession()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    @property
    def host(self) -> str:
        return self.app.host

    @property
    def port(self) -> int:
        return self.app.port

    def ws_connect(self, path: str) -> http.AsyncContextManager[http.Websocket]:
        """
        Performs a websocket connection.

        Parameters:
            path: The path to the websocket.

        Returns:
            A context manager for the websocket.

        Example:
            ```py
            import railway

            app = railway.Application()
            client = railway.TestClient(app)

            @app.websocket('/ws')
            async def handler(request: railway.Request, ws: railway.Websocket):
                await ws.send(b'Hello!')

                data = await ws.recieve()
                print(data.data)

                await ws.close()

            async def main():
                async with app:
                    async with client.ws_connect('/ws') as ws:
                        message = await ws.recieve_str()
                        print(message)

                        await ws.send(b'Hi!')
            
            app.loop.run_until_complete(main())
            ```
        """
        url = self.app.url_for(path, is_websocket=True)
        return self.session.ws_connect(str(url))

    def request(self, path: str, method: str, **kwargs: Any) -> http.AsyncContextManager[http.HTTPResponse]:
        """
        Sends a request to the application.

        Parameters
        
            path: The path to the resource.
            method: The HTTP method.
            **kwargs: Additional arguments to pass to the request.

        Returns:
            A context manager for the request.

        Example:
            ```py
            import railway

            app = railway.Application()
            client = railway.TestClient(app)

            @app.route('/')
            async def index(request: railway.Request):
                return 'another creative response'

            async def main():
                async with app:
                    async with client.get('/') as response:
                        print(response.status)
                        text = await response.text()

                        print(text)

            app.loop.run_until_complete(main())
            ```
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


    
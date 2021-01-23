# async-web-stuff

## Example Usage

```python
import wsgi
import asyncio
import typing

loop = asyncio.get_event_loop()
app = wsgi.Application(loop=loop)

@app.listen()
async def on_startup(host: str, port: int):
    print(f'Running on {host}:{port}')

@app.route('/', 'GET')
async def index(request: wsgi.Request):
    return 'Hello, World!'

@app.middleware()
async def middleware(request: wsgi.Request, handler: typing.Coroutine):
    print(f'Recieved a {request.method!r} request over at {request.url.raw_path!r}')

    return await handler(request)

if __name__ == '__main__':
    app.run('127.0.0.1', port=8080)
```

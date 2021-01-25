import os
import wsgi
import asyncio

import typing
import pathlib

path = pathlib.Path('.')

loop = asyncio.get_event_loop()
app = wsgi.Application(loop=loop)

@app.route('/', 'GET')
async def index(request: wsgi.Request):
    return '!'

@app.get('/te')
async def tes(req):
    return '?'

@app.route('/ye/e', 'GET')
async def uegbofe(res):
    return ''

@app.middleware()
async def middleware(request: wsgi.Request, coro: typing.Coroutine):
    print(f'[{app.__datetime}] Recieved a {request.method!r} at {request.url.raw_path!r}')

    return await coro(request)

@app.listen('on_startup')
async def star():
    print(app.routes)

@app.listen('on_restart')
async def restsrt():
    print('RE')



if __name__ == '__main__': app.run('127.0.0.1', port=8080, debug=True)


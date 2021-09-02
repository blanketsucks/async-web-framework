import atom
import asyncio

app = atom.Application(use_ssl=True)
    
@app.route('/')
async def requ(wwfw):
    return '<h1>Hello, World!</h1>'

@requ.middleware
async def middleware(request, handler):
    print(request.path)
    return await handler(request)

@app.event('123213')
async def pa(): return '123'

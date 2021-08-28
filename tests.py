import atom
import asyncio

app = atom.Application()

@app.route('/')
async def main(request: atom.Request):
    return 'yes'

@main.middleware
async def middleware(route: atom.Route, request: atom.Request):
    if request.text() == 'ok':
        await request.send('no')
        return

asyncio.run(atom.run(app))
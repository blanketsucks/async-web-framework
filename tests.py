import asyncio
import atom

app = atom.Application(port=4443, use_ssl=True)

@app.get('/')
async def index(request):
    return 'ok'

asyncio.run(atom.run(app))
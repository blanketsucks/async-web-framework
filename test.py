import asyncio
from typing import Union
import atom

app = atom.Application(suppress_warnings=True)

@app.route('/')
def index(request):
    raise Exception('Exception occured')

@app.event('on_error')
async def on_error(route: Union[atom.PartialRoute, atom.Route], request: atom.Request, error: Exception):
    print(f'{route} {request} {error}')

asyncio.run(atom.run(app))
                
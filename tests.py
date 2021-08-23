import asyncio
import atom
from atom import oauth

app = atom.Application()
client = atom.TestClient(app)

@app.route('/')
async def index(request):
    return 'Hello, World!'

@app.event('on_worker_startup')
async def on_worker_startup(worker: atom.Worker):
    print(f'Worker-{worker.id} has started')

@app.event('on_worker_shutdown')
async def on_worker_shutdown(worker: atom.Worker):
    print(f'Worker-{worker.id} has shutdown')

if __name__ == '__main__':
    async def main():
        async with client.ws_connect('/feed') as websocket:
            pass
    
    asyncio.run(main())

from wsgi import restful
from wsgi import tasks
import wsgi

app = wsgi.Application()

@app.listen('on_startup')
async def start():
    print('START')

@app.route('/', 'GET')
async def index(request):
    return {request.url: request.headers}


if __name__ == '__main__':
    app.loop.run_until_complete(app.start())


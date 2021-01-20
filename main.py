
from wsgi import Route, Listener, restful, html, database
db = database.PostgresConnection()

async def index(request):
    return html('yes.html')

async def on_startup(host: str, port: int):
    print('Running on {0!r}:{1}'.format(host, port))

routes = [
    Route('/', 'GET', index)
]
listeners = [
    Listener(on_startup, 'on_startup')
]
extensions = [
    'exttest'
]

app = restful.RESTApp(routes=routes, listeners=listeners, extensions=extensions)

app.run()

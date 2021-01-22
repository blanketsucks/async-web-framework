
from wsgi import Request
from wsgi import tasks
from wsgi import database

INFO = {
    "database": "Main",
    "user": "postgres",
    "password": "blanketsucks"
}

from wsgi.restful import App
from wsgi.helpers import jsonify


import asyncio
loop = asyncio.get_event_loop()

app = App(loop=loop)
db = database.PostgresConnection(loop=loop, app=app)

@app.listen('on_startup')
async def startup(host, port):
    await db.connect(**INFO)

@app.listen('on_database_connect')
async def connected(conn):
    print(conn)
    print('database connected')

@app.listen('on_shutdown')
async def close():
    await db.close()
    print('closed')

@app.get('/')
async def index(request: Request):
    res = await db.fetch_all('SELECT * FROM economy')

    return jsonify(welcome=f'{res}')

@tasks.task(minutes=1, count=10)
async def refresh():
    print('refreshed')

app.run()

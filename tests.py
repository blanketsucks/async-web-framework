import wsgi
from wsgi import helpers
from wsgi import restful

app = restful.App()

@app.listen('on_startup')
async def start(host, port):
    print('Running on {0}:{1}'.format(host, port))

@app.route('/user/{username}', 'GET')
async def get_user(request: wsgi.Request):
    username = request.args['username']
    return username

@app.route('/users', 'GET')
async def all(request: wsgi.Request):
    return {}

app.run()
import wsgi

from wsgi import restful
from wsgi import helpers

app = restful.App()

@app.route('/', 'GET')
async def index(request: wsgi.Request):
    return helpers.jsonify(Hello='World!')

app.run()
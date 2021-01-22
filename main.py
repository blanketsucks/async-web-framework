
import wsgi
from wsgi.helpers import jsonify

app = wsgi.Application()

@app.protected('/', 'GET')
async def req(request: wsgi.Request):
    return jsonify(yes='no')

app.run()
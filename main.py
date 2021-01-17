from wsgi import Application, jsonify
from wsgi.ext import tasks

app = Application()

app.load_extension('exttest')

@app.route('/path', 'GET')
async def path(request):
    return jsonify(hello='yes')

@tasks.task(seconds=1, count=5, loop=app.loop)
async def starttask():
    print('yus')

starttask.start()
app.run()
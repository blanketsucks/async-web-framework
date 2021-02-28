import atom
from atom import restful

app = restful.RESTApplication()
print(app)
@atom.task(seconds=10)
async def task():

    async with app.request('/test', 'GET') as req:
        print(req)

@app.route('/test', 'GET')
async def index(ctx: atom.Context):
    ctx.build_response('hehehehe')
    return ctx

@app.route('/yes', 'GET')
async def yes(ctx: atom.Context):
    ctx.build_response('yes')

    return ctx

@app.listen('on_startup')
async def test():
    task.start()

# app.run()
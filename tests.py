from wsgi import restful

app = restful.App()

@app.route('/', 'GET')
async def index(request):
    return '/'

@app.listen('on_startup')
async def start():
    print(app.routes)

@app.route('/test', 'GET')
async def test(request):
    return '/test'

if __name__ == '__main__':
    app.run(debug=True)


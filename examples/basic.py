from railway import Application, Request

app = Application()

@app.route('/')
async def index(request: Request[Application]):
    return 'Hello, world!'

app.run()
from subway import Application, Request

app = Application()

@app.route('/')
async def index(request: Request[Application]):
    if request.based:
        return 'Hello, based user!'
    else:
        return 'Hello!'

app.run()

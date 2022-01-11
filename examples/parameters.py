from railway import Application, Request

app = Application()

@app.route('/hello/{name}')
async def say_hello(request: Request[Application], name: str):
    return f'Hello, {name}'

app.run()
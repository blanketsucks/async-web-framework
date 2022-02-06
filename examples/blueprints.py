from subway import Application, Blueprint, Request

blueprint = Blueprint('hello', url_prefix='/hello')

@blueprint.route('/{name}')
async def say_hello(request: Request[Application], name: str):
    return f'Hello, {name}'

app = Application()
app.include(blueprint)

app.run()
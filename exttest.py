from wsgi.ext import extensions
from wsgi import jsonify

class Cog(extensions.Extension):
    def __init__(self, app) -> None:
        self.app = app

    @extensions.Extension.listener()
    async def on_startup(self):
        print('Ready')

    @extensions.Extension.route('/', 'GET')
    async def index(self, request):
        return jsonify(test='hiiiiii')

def load(app):
    app.add_extension(Cog(app))
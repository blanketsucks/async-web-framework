from wsgi import restful
from wsgi import jsonify

class Cog(restful.Extension):
    def __init__(self, app) -> None:
        self.app = app

    @restful.Extension.listener()
    async def on_startup(self, host, port):
        print('Ready')

    @restful.Extension.route('/yeet', 'GET')
    async def index(self, request):
        return jsonify(test='hiiiiii')

def load(app):
    app.add_extension(Cog(app))
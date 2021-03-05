import atom

app = atom.Application()

class View(atom.HTTPView, path='/users'):
    async def get(self, ctx: atom.Context):
        return ctx.build_json_response(
            {
                'Hello': ', World!'
            }
        )

app.register_view(View())
app.run()
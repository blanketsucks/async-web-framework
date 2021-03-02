
import atom

app = atom.Application()

@app.route('/hello/{name}', 'GET')
async def get_name(ctx: atom.Context, name: str):
    if len(name) > 64:
        return atom.abort(400, message={'error': 'name argument too long'}, content_type='application/json')

    ctx.build_json_response({'Hello there': name})
    return ctx

if __name__ == '__main__':
    app.run()

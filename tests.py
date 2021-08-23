import atom
import asyncio

app = atom.Application()

@app.route('/hello/{name}', 'GET')
async def get_name(request: atom.Request, name: str):
    if len(name) > 25:
        error = {
            'message': 'name too long.',
            'status': 400
        }
        return error, 400

    return {
        'Hello': name
    }

if __name__ == '__main__':
    asyncio.run(atom.run(app))

# async-web-stuff

## Example Usages

### Basic Example

```py
import atom

app = atom.Application()

@app.route('/hello/{name}', 'GET')
async def get_name(request: atom.Request, name: str):
    if len(name) > 64:
        error = {
            'error': 'name too long.
        }
        return atom.abort(400, message=error, content_type='application/json')

    return {
        'Hello': name
    }

if __name__ == '__main__':
    app.run()

```

### Views Example

```py
import atom

app = atom.Application()
app.users = {}

@app.view('/users') # Either this or class UsersView(atom.HTTPView, path='/users'), both work
class UsersView(atom.HTTPView):
    async def get(self, request: atom.Request):
        return app.users

if __name__ == '__main__':
    app.run()
```

### Oauth example

```py
from atom.oauth import discord
import atom

oauth = discord.Oauth2Client(
    client_id="",
    client_secret="",
    redirect_uri="http://127.0.0.1:8080/callback",
)

app = atom.Application()

@app.get('/login')
async def login(request: atom.Request):
    return oauth.redirect(request)

@app.get('/callback')
async def callback(request: atom.Request):
    code = request.params.get('code')
    session = oauth.create_session(code)

    response = request.redirect('/guilds?code={}'.format(session.code))
    return response

@app.get('/guilds')
async def guilds(request: atom.Request):
    code = request.params.get('code')
    session = oauth.get_session(code)

    guilds = await session.user.fetch_guilds()
    return atom.JSONResponse(body=[guild.to_dict() for guild in guilds])

if __name__ == '__main__':
    app.run(port=8080)
```
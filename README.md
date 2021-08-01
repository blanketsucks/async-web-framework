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
        return request.app.users

if __name__ == '__main__':
    app.run()
```

### Oauth example

```py
import atom
from atom.oauth import discord

app = atom.Application(supress_warnings=True)
router = atom.Router()

app.settings['SESSION_COOKIE_NAME'] = 'cookie_name'

oauth = discord.Oauth2Client(
    client_id='',
    client_secret='',
    redirect_uri='http://127.0.0.1:8080/callback'
)

@router.get('/callback')
async def index(request: atom.Request):
    token, code = request.session.get('code')
    if code:
        return request.redirect('/home')

    code = request.url.query.get('code')
    if not code:
        return request.redirect('/login')

    session = oauth.create_session(code)
    token = await session.fetch_token()

    request.session['code'] = (token['access_token'], code)
    return request.redirect('/home')

@router.get('/')
async def index(request: atom.Request):
    code = request.url.query.get('code')
    if not code:
        return request.redirect('/login')

    session = await oauth.create_session(code)
    request.session['code'] = (session.access_token, code)

    return request.redirect('/home')

@router.get('/login')
def redirect(request: atom.Request):
    token, code = request.session.get('code')
    if code:
        return request.redirect('/home')

    return oauth.redirect(request)

app.add_router(router)

if __name__ == '__main__':
    app.run()
```
import atom
from atom.oauth import discord

app = atom.Application(supress_warnings=True)
router = atom.Router()

app.settings['SESSION_COOKIE_NAME'] = 'olfsk'

app.settings.authentication.set_credentials_for(
    service='discord',
    client_id='',
    client_secret='',
    redirect_uri='http://127.0.0.1:8080/'
)

credentials = app.settings.authentication.get_credentials_for('discord')

oauth = discord.Oauth2Client(
    client_id=credentials.client_id,
    client_secret=credentials.client_secret,
    redirect_uri=credentials.redirect_uri,
)

@router.get('/')
async def index(request: atom.Request):
    code = request.url.query.get('code')
    if not code:
        return request.redirect('/login')

    session = oauth.create_session(code)
    token = await session.fetch_token()

    request.session['user_token'] = (token, code)
    return request.redirect('/home')

@router.get('/home')
async def home(request: atom.Request):
    token, code = request.session.get('user_token')
    if not token:
        return request.redirect('/login')

    session = oauth.get_session(code)
    user = await session.fetch_user()

    return atom.JSONResponse(user.to_dict())

@router.get('/login')
def redirect(request: atom.Request):
    if request.session:
        token, code = request.session.get('user_token')
        if code:
            return request.redirect('/home')

    return oauth.redirect(request)

app.add_router(router)
app.run()
from atom.response import JSONResponse
from atom.oauth import discord, github
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
    return JSONResponse(body=guilds)

app.run(port=8080)
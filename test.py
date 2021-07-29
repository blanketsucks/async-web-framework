from atom.response import JSONResponse
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
    return oauth.redirect(request, scopes=['identify', 'guilds'])

@app.get('/callback')
async def callback(request: atom.Request):
    code = request.params.get('code')
    session = oauth.create_session(code)

    response = request.redirect('/guilds')
    response.set_cookie('code', code)

    return response

@app.get('/guilds')
async def guilds(request: atom.Request):
    code = request.cookies.get('code')
    session = oauth.get_session(code)
    
    user = await session.fetch_user()
    guilds = await user.fetch_guilds()

    return JSONResponse(body=[guild.to_dict() for guild in guilds])

app.run(port=8080)
from atom.response import JSONResponse
from atom.oauth import discord
import atom

oauth = discord.Oauth2Client(
    client_id="",
    client_secret="",
    redirect_uri="http://127.0.0.1:8080/callback",
)

app = atom.Application()

value = app.settings['21332132131231']
print(value)


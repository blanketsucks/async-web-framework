
import atom
import typing
import inspect


app = atom.Application()

@app.get('/api/users/{username}/guild/{guildid}')
async def get_guild_user(request: atom.Request, username: str, guildid: int):
    return f'{username}, {guildid}'
    

@app.listen()
async def on_error(error):
    raise error

app.run()
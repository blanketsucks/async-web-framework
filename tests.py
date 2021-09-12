import io
import railway
import cProfile
import pstats

app = railway.Application()
profile = cProfile.Profile()

profile.enable()

@app.get('/profile')
async def prof(request: railway.Request):
    stdout = io.StringIO()
    stats = pstats.Stats(profile, stream=stdout)

    stats.print_stats()
    profile.disable()

    return stdout.getvalue()

app.run()


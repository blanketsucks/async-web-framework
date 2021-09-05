import railway
import logging

logging.basicConfig(level=logging.DEBUG)

app = railway.Application()

@app.get('/')
async def index(request):
    return 'Hello, World!'

app.run()

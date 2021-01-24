import wsgi
import asyncio
loop = asyncio.get_event_loop()

app = wsgi.Application(loop=loop)

@app.route('/test', 'GET')
async def test(request):
    return ''

if __name__ == '__main__':
    app.run(debug=True)
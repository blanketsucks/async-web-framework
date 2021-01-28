import atom

app = atom.Application()

@app.route('/restart', 'GET')
async def restart(request):
    await app.restart() # lol

@app.route('/close', 'GET')
async def close(request):
    await app.close() # lol

if __name__ == '__main__':
    app.run()
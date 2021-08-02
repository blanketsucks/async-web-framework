import atom
app = atom.Application()

@app.get('/download/{filename}')
async def download(request: atom.Request, filename: str):
    try:
        file = atom.File(filename + '.py')
    except FileNotFoundError:
        return atom.NotFound()

    return file

app.run()
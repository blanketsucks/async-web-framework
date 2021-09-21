import railway

app = railway.Application()

@app.route('/', '*')
async def index(request):
    pass

print(index.method)
print(app.router.routes)
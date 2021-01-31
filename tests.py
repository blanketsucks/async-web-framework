
from atom.utils import markdown
import atom

app = atom.Application()

@app.get('/docs')
async def docs(req):
    return markdown('README.md')

app.run()
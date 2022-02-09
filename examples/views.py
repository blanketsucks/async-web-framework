from subway import Application, Request, HTTPView

app = Application()

@app.view() # Pass in `path` here or in the class kwargs.
class View(HTTPView, path='/hello/{name}'): # Parameters also work with views.
    async def get(self, request: Request, name: str):
        return name

app.run()
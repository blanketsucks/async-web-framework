import jinja2
from .response import HTMLResponse
from typing import Any, Dict

async def render(
    path: str,
    env: jinja2.Environment=..., 
    globals: Dict[str, Any]=..., 
    locals: Dict[str, Any]=..., 
    **kwargs: Any
) -> HTMLResponse: ...

import jinja2
from .response import HTMLResponse
from typing import Any, Dict

def create_default_jinja2_env() -> jinja2.Environment: ...
async def render(
    path: str,
    env: jinja2.Environment=..., 
    __globals: Dict[str, Any]=..., 
    __locals: Dict[str, Any]=..., 
    **kwargs: Any
) -> HTMLResponse: ...

from typing import Any, Callable, Dict, Union
import json

__all__ = (
    'create_function',
    'is_json_serializable',
    'model_getattr',
)

def create_function(name: str, body: str) -> Callable[..., Any]:
    txt = f"def __create_fn__():\n {body}\n return {name}"

    namespace: Dict[str, Any] = {}
    exec(txt, {}, namespace)

    return namespace['__create_fn__']()

def is_json_serializable(obj: Any) -> bool:
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False

def model_getattr(obj: Any, name: str) -> Any:
    from .models import Model

    attr = getattr(obj, name, None)
    if isinstance(attr, Model):
        return attr.json()

    return attr

def is_optional(annotation: Any) -> bool:
    origin = getattr(annotation, '__origin__', None)
    if origin is not None:
        return origin is Union and type(None) in annotation.__args__
    else:
        return False

class Default:
    def __repr__(self) -> str:
        return '<default>'

    def __bool__(self) -> bool:
        return False

DEFAULT: Any = Default()
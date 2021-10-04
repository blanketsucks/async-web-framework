import pathlib
import ssl
from typing import Any, Dict, Optional, Tuple, TypedDict, Union

VALID_SETTINGS: Tuple[str, ...] = ...
DEFAULT_SETTINGS: Dict[str, Any] = ...

class Settings(TypedDict):
    host: str
    port: int
    url_prefix: str
    use_ipv6: bool
    ssl_context: Optional[ssl.SSLContext]
    worker_count: int
    session_cookie_name: Optional[str]
    backlog: int
    max_concurent_requests: Optional[int]
    max_pending_connections: int
    connection_timeout: Optional[int]

def settings_from_file(path: Union[str, pathlib.Path]) -> Settings: ...
def settings_from_env() -> Settings: ...

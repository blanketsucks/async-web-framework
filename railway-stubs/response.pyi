import enum
from .file import File
from .cookies import CookieJar
from typing import Any, Dict, List, Optional, Union

class HTTPStatus(enum.IntEnum):
    def __new__(cls: Any, value: int, description: str) -> Any: ...
    @property
    def status(self) -> int: ...
    @property
    def description(self) -> str: ...
    CONTINUE: HTTPStatus
    SWITCHING_PROTOCOLS: HTTPStatus
    PROCESSING: HTTPStatus
    EARLY_HINTS: HTTPStatus
    OK: HTTPStatus
    CREATED: HTTPStatus
    ACCEPTED: HTTPStatus
    NON_AUTHORITATIVE_INFORMATION: HTTPStatus
    NO_CONTENT: HTTPStatus
    RESET_CONTENT: HTTPStatus
    PARTIAL_CONTENT: HTTPStatus
    MULTI_STATUS: HTTPStatus
    ALREADY_REPORTED: HTTPStatus
    IM_USED: HTTPStatus
    MULTIPLE_CHOICES: HTTPStatus
    MOVED_PERMANENTLY: HTTPStatus
    FOUND: HTTPStatus
    SEE_OTHER: HTTPStatus
    NOT_MODIFIED: HTTPStatus
    USE_PROXY: HTTPStatus
    TEMPORARY_REDIRECT: HTTPStatus
    PERMANENT_REDIRECT: HTTPStatus
    BAD_REQUEST: HTTPStatus
    UNAUTHORIZED: HTTPStatus
    PAYMENT_REQUIRED: HTTPStatus
    FORBIDDEN: HTTPStatus
    NOT_FOUND: HTTPStatus
    METHOD_NOT_ALLOWED: HTTPStatus
    NOT_ACCEPTABLE: HTTPStatus
    PROXY_AUTHENTICATION_REQUIRED: HTTPStatus
    REQUEST_TIMEOUT: HTTPStatus
    CONFLICT: HTTPStatus
    GONE: HTTPStatus
    LENGTH_REQUIRED: HTTPStatus
    PRECONDITION_FAILED: HTTPStatus
    REQUEST_ENTITY_TOO_LARGE: HTTPStatus
    REQUEST_URI_TOO_LONG: HTTPStatus
    UNSUPPORTED_MEDIA_TYPE: HTTPStatus
    REQUESTED_RANGE_NOT_SATISFIABLE: HTTPStatus
    EXPECTATION_FAILED: HTTPStatus
    IM_A_TEAPOT: HTTPStatus
    MISDIRECTED_REQUEST: HTTPStatus
    UNPROCESSABLE_ENTITY: HTTPStatus
    LOCKED: HTTPStatus
    FAILED_DEPENDENCY: HTTPStatus
    TOO_EARLY: HTTPStatus
    UPGRADE_REQUIRED: HTTPStatus
    PRECONDITION_REQUIRED: HTTPStatus
    TOO_MHTTPStatus_REQUESTS: HTTPStatus
    REQUEST_HEADER_FIELDS_TOO_LARGE: HTTPStatus
    UNAVAILABLE_FOR_LEGAL_REASONS: HTTPStatus
    INTERNAL_SERVER_ERROR: HTTPStatus
    NOT_IMPLEMENTED: HTTPStatus
    BAD_GATEWAY: HTTPStatus
    SERVICE_UNAVAILABLE: HTTPStatus
    GATEWAY_TIMEOUT: HTTPStatus
    HTTP_VERSION_NOT_SUPPORTED: HTTPStatus
    VARIANT_ALSO_NEGOTIATES: HTTPStatus
    INSUFFICIENT_STORAGE: HTTPStatus
    LOOP_DETECTED: HTTPStatus
    NOT_EXTENDED: HTTPStatus
    NETWORK_AUTHENTICATION_REQUIRED: HTTPStatus

class Response:
    version: str
    cookies: CookieJar
    def __init__(self, body: Optional[str]=..., status: Optional[int]=..., content_type: Optional[str]=..., headers: Optional[Dict[str, Any]]=..., version: Optional[str]=...) -> None: ...
    @property
    def body(self) -> Any: ...
    @body.setter
    def body(self, value: Any) -> None: ...
    @property
    def status(self) -> HTTPStatus: ...
    @property
    def content_type(self) -> str: ...
    @property
    def headers(self) -> Dict[str, Any]: ...
    def add_body(self, data: str) -> None: ...
    def add_header(self, key: str, value: str) -> Any: ...
    def add_cookie(self, name: str, value: str, *, domain: Optional[str]=..., http_only: bool=..., is_secure: bool=...) -> Any: ...
    def encode(self) -> bytes: ...

class HTMLResponse(Response):
    def __init__(self, body: Optional[str]=..., status: Optional[int]=..., headers: Optional[Dict[str, Any]]=..., version: Optional[str]=...) -> None: ...

class JSONResponse(Response):
    def __init__(self, body: Optional[Union[Dict[str, Any], List[Any]]]=..., status: Optional[int]=..., headers: Optional[Dict[str, Any]]=..., version: Optional[str]=...) -> None: ...

class FileResponse(Response):
    file: File
    def __init__(self, file: File, status: Optional[int]=..., headers: Optional[Dict[str, str]]=..., version: Optional[str]=...) -> None: ...
    def get_content_type(self) -> str: ...
    async def read(self) -> bytes: ...

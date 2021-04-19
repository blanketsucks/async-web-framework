import enum

__all__ = (
    'HTTPStatus',
    'WebSocketOpcode',
    'WebSocketCloseCode',
    'WebSocketState'
)

class HTTPStatus(enum.IntEnum):
    def __new__(cls, value: int, description: str):
        self = int.__new__(cls, value)

        self._value_ = value
        self._description_ = description

        return self

    @property
    def full(self):
        return (self.value, self.description)

    @property
    def description(self):
        return self._description_

    CONTINUE = 100, 'Continue'
    SWITCHING_PROTOCOLS = 101, 'Switching Protocols'
    PROCESSING = 102, 'Processing'
    EARLY_HINTS = 103, 'Early Hints'
    OK = 200, 'OK'
    CREATED = 201, 'Created'
    ACCEPTED = 202, 'Accepted'
    NON_AUTHORITATIVE_INFORMATION = 203, 'Non-Authoritative Information'
    NO_CONTENT = 204, 'No Content'
    RESET_CONTENT = 205, 'Reset Content'
    PARTIAL_CONTENT = 206, 'Partial Content'
    MULTI_STATUS = 207, 'Multi-Status'
    ALREADY_REPORTED = 208, 'Already Reported'
    IM_USED = 226, 'IM Used'
    MULTIPLE_CHOICES = 300, 'Multiple Choices'
    MOVED_PERMANENTLY = 301, 'Moved Permanently'
    FOUND = 302, 'Found'
    SEE_OTHER = 303, 'See Other'
    NOT_MODIFIED = 304, 'Not Modified'
    USE_PROXY = 305, 'Use Proxy'
    TEMPORARY_REDIRECT = 307, 'Temporary Redirect'
    PERMANENT_REDIRECT = 308, 'Permanent Redirect'
    BAD_REQUEST = 400, 'Bad Request'
    UNAUTHORIZED = 401, 'Unauthorized'
    PAYMENT_REQUIRED = 402, 'Payment Required'
    FORBIDDEN = 403, 'Forbidden'
    NOT_FOUND = 404, 'Not Found'
    METHOD_NOT_ALLOWED = 405, 'Method Not Allowed'
    NOT_ACCEPTABLE = 406, 'Not Acceptable'
    PROXY_AUTHENTICATION_REQUIRED = 407, 'Proxy Authentication Required'
    REQUEST_TIMEOUT = 408, 'Request Timeout'
    CONFLICT = 409, 'Conflict'
    GONE = 410, 'Gone'
    LENGTH_REQUIRED = 411, 'Length Required'
    PRECONDITION_FAILED = 412, 'Precondition Failed'
    REQUEST_ENTITY_TOO_LARGE = 413, 'Request Entity Too Large'
    REQUEST_URI_TOO_LONG = 414, 'Request-URI Too Long'
    UNSUPPORTED_MEDIA_TYPE = 415, 'Unsupported Media Type'
    REQUESTED_RANGE_NOT_SATISFIABLE = 416, 'Requested Range Not Satisfiable'
    EXPECTATION_FAILED = 417, 'Expectation Failed'
    IM_A_TEAPOT = 418, 'I\'m a Teapot'
    MISDIRECTED_REQUEST = 421, 'Misdirected Request'
    UNPROCESSABLE_ENTITY = 422, 'Unprocessable Entity'
    LOCKED = 423, 'Locked'
    FAILED_DEPENDENCY = 424, 'Failed Dependency'
    TOO_EARLY = 425, 'Too Early'
    UPGRADE_REQUIRED = 426, 'Upgrade Required'
    PRECONDITION_REQUIRED = 428, 'Precondition Required'
    TOO_MANY_REQUESTS = 429, 'Too Many Requests'
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431, 'Request Header Fields Too Large'
    UNAVAILABLE_FOR_LEGAL_REASONS = 451, 'Unavailable For Legal Reasons'
    INTERNAL_SERVER_ERROR = 500, 'Internal Server Error'
    NOT_IMPLEMENTED = 501, 'Not Implemented'
    BAD_GATEWAY = 502, 'Bad Gateway'
    SERVICE_UNAVAILABLE = 503, 'Service Unavailable'
    GATEWAY_TIMEOUT = 504, 'Gateway Timeout'
    HTTP_VERSION_NOT_SUPPORTED = 505, 'HTTP Version Not Supported'
    VARIANT_ALSO_NEGOTIATES = 506, 'Variant Also Negotiates'
    INSUFFICIENT_STORAGE = 507, 'Insufficient Storage'
    LOOP_DETECTED = 508, 'Loop Detected'
    NOT_EXTENDED = 510, 'Not Extended'
    NETWORK_AUTHENTICATION_REQUIRED = 511, 'Network Authentication Required'

class WebSocketOpcode(enum.IntEnum):
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA

class WebSocketCloseCode(enum.IntEnum):
    NORMAL = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED = 1003
    RESERVED = 1004
    NO_STATUS = 1005
    ABNORMAL = 1006
    UNSUPPORTED_PAYLOAD = 1007
    POLICY_VIOLATION = 1008
    TOO_LARGE = 1009
    MANDATORY_EXTENSION = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    BAD_GATEWAY = 1014
    TLS_HANDSHAKE = 1015

class WebSocketState(enum.IntEnum):
    CLOSED = 0
    CONNECTED = 1
    READING = 2
    SENDING = 3
    HANDSHAKING = 4
import enum
from typing import Tuple

__all__ = (
    'WebsocketState',
    'WebsocketOpcode',
    'WebsocketCloseCode',
    'VALID_OPCODES',
    'VALID_CLOSE_CODES',
    'UNASSIGNED_NON_CONTROL_OPCODES',
    'UNASSIGNED_CONTROL_OPCODES'
)

class WebsocketState(enum.Enum):
    """
    An enumeration.
    """
    CONNECTING = 0
    OPEN = 1
    SENDING = 2
    RECEIVING = 3
    CLOSED = 4
    CLOSING = 5

class WebsocketOpcode(enum.IntEnum):
    """
    An enumeration.
    """
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA

class WebsocketCloseCode(enum.IntEnum):
    """
    An enumeration. \
    Taken from https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code#value

    Attributes
    ----------
    value: :class:`int`
        The value of the enum.
    name: :class:`str`
        The name of the enum.
    description: :class:`str`
        A description of the close code.
    reason: :class:`str`
        The reason for the close code.
    """
    description: str
    reason: str

    def __new__(cls, value: int, reason: str='', description: str='') -> 'WebsocketCloseCode':
        obj = int.__new__(cls, value)

        obj._value_ = value
        obj.reason = reason
        obj.description = description

        obj.__doc__ = description
        return obj

    NORMAL = 1000, 'Normal Closure', \
        'Normal closure; the connection successfully completed whatever purpose for which it was created.'
    GOING_AWAY = 1001, 'Going Away', \
         'The endpoint is going away, either because of a server failure or because the browser is navigating away from the page that opened the connection.'
    PROTOCOL_ERROR = 1002, 'Protocol Error', \
        'The endpoint is terminating the connection due to a protocol error.'
    UNSUPPORTED = 1003, 'Unsupported Data', \
        'The connection is being terminated because the endpoint received data of a type it cannot accept (for example, a text-only endpoint received binary data).'
    RESERVED = 1004, 'Reserved', \
        'Reserved for future use by the WebSocket standard.'
    NO_STATUS = 1005, 'No Status Received', \
        'Indicates that no status code was provided even though one was expected.'
    ABNORMAL = 1006, 'Abnormal Closure', \
        'Used to indicate that a connection was closed abnormally (that is, with no close frame being sent) when a status code is expected.'
    UNSUPPORTED_PAYLOAD = 1007, 'Unsupported Payload Data', \
        'Indicates that an endpoint is terminating the connection because it received a message that contained inconsistent data (e.g., non-UTF-8 data within a text message).'
    POLICY_VIOLATION = 1008, 'Policy Violation', \
        'Indicates that an endpoint is terminating the connection because it received a message that violates its policy. This is a generic status code, used when codes 1003 and 1009 are not suitable.'
    TOO_LARGE = 1009, 'Message Too Large', \
        'Indicates that an endpoint is terminating the connection because it received a message that is too big for it to process.'
    MANDATORY_EXTENSION = 1010, 'Mandatory Extension', \
        'Indicates that an endpoint (client) is terminating the connection because it expected the server to negotiate one or more extension, but the server didn\'t.'
    INTERNAL_ERROR = 1011, 'Internal Error', \
        'Indicates that an endpoint is terminating the connection because it encountered an unexpected condition that prevented it from fulfilling the request.'
    SERVICE_RESTART = 1012, 'Service Restart', \
        'Indicates that the service will be restarted.'
    TRY_AGAIN_LATER = 1013, 'Try Again Later', \
        'Indicates that the service is restarted after a temporary interruption.'
    BAD_GATEWAY = 1014, 'Bad Gateway', \
        'Indicates that the server, while acting as a gateway or proxy, received an invalid response from the upstream server it accessed in attempting to fulfill the request.'
    TLS_HANDSHAKE = 1015, 'TLS Handshake', \
        'Indicates that the connection was closed due to a failure to perform a TLS handshake (e.g., the server certificate can\'t be verified).'


UNASSIGNED_NON_CONTROL_OPCODES: Tuple[int, ...] = (0x4, 0x5, 0x6, 0x7)
UNASSIGNED_CONTROL_OPCODES: Tuple[int, ...] = (0xB, 0xC, 0xD, 0xE, 0xF)


VALID_OPCODES = {opcode.value for opcode in WebsocketOpcode}
VALID_OPCODES.update(
    UNASSIGNED_NON_CONTROL_OPCODES,
    UNASSIGNED_CONTROL_OPCODES
)

VALID_CLOSE_CODES = {code.value for code in WebsocketCloseCode}


from subway.errors import RailwayException

__all__ = (
    'WebSocketError',
    'InvalidWebSocketFrame',
    'InvalidWebSocketCloseCode',
    'InvalidWebSocketOpcode',
    'InvalidWebSocketControlFrame',
    'FragmentedControlFrame'
)


class WebSocketError(RailwayException):
    """
    Base class for all websocket related errors.
    """


class WebSocketWarning(Warning):
    """
    A warning related to websocket operations.
    """


class InvalidWebSocketFrame(WebSocketError):
    """
    Base class for all invalid non-control frames errors.
    """


class InvalidWebSocketCloseCode(InvalidWebSocketFrame):
    """
    Raised when a close frame is received with an invalid code.
    """
    def __init__(self, code: int) -> None:
        self.code = code
        super().__init__(f'Received an invalid close code: {code}')


class InvalidWebSocketOpcode(InvalidWebSocketFrame):
    """
    Raised when an invalid opcode is received.
    """
    def __init__(self, opcode: int) -> None:
        self.opcode = opcode
        super().__init__(f'Received an invalid opcode: {opcode}')


class InvalidWebSocketControlFrame(WebSocketError):
    """
    Base class for all invalid control frames errors.
    """


class FragmentedControlFrame(InvalidWebSocketControlFrame):
    """
    Raised whenever a control frame is fragmented.
    """
    def __init__(self, received: bool = True) -> None:
        if received:
            message = 'Received a fragmented control frame'
        else:
            message = 'Control frames must not be fragmented'

        super().__init__(message)
        
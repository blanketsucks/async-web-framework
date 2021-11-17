
from railway.errors import RailwayException

__all__ = (
    'WebsocketError',
    'InvalidWebsocketFrame',
    'InvalidWebsocketCloseCode',
    'InvalidWebsocketOpcode',
    'InvalidWebsocketControlFrame',
    'FragmentedControlFrame'
)

class WebsocketError(RailwayException):
    """
    Base class for all websocket related errors.
    """

class InvalidWebsocketFrame(WebsocketError):
    """
    Base class for all invalid non-control frames errors.
    """

class InvalidWebsocketCloseCode(InvalidWebsocketFrame):
    """
    Raised when a close frame is received with an invalid code.
    """
    def __init__(self, code: int) -> None:
        self.code = code
        super().__init__(f'Received an invalid close code: {code}')

class InvalidWebsocketOpcode(InvalidWebsocketFrame):
    """
    Raised when an invalid opcode is received.
    """
    def __init__(self, opcode: int) -> None:
        self.opcode = opcode
        super().__init__(f'Received an invalid opcode: {opcode}')

class InvalidWebsocketControlFrame(WebsocketError):
    """
    Base class for all invalid control frames errors.
    """

class FragmentedControlFrame(InvalidWebsocketControlFrame):
    """
    Raised whenever a control frame is fragmented.
    """
    def __init__(self, received: bool = True) -> None:
        if received:
            message = 'Received a fragmented control frame'
        else:
            message = 'Control frames must not be fragmented'

        super().__init__(message)
        
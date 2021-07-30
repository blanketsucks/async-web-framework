
class OauthException(Exception):
    """
    Base exception for all oauth related errors.
    """
    pass


class InvalidOauth(OauthException):
    """
    Raised when the oauth token is invalid.
    """
    pass


class SessionError(OauthException):
    """
    Raised when there is an error with the session.
    """
    pass

class SessionClosed(SessionError):
    """
    Raised when the session is closed.
    """
    pass
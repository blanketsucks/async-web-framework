from .response import Response, responses
import json

excs = {}

__all__ = (
    'AppError',
    'BadConversion',
    'HTTPException',
    'NotFound',
    'BadRequest',
    'Found',
    'Unauthorized',
    'Forbidden',
    'EndpointError',
    'EndpointLoadError',
    'EndpointNotFound',
    'ExtensionLoadError',
    'ExtensionError',
    'ExtensionNotFound',
    'RegistrationError',
    'RouteRegistrationError',
    'ListenerRegistrationError',
    'MiddlewareRegistrationError',
    'ShardRegistrationError',
    'ViewRegistrationError',
    'WebsocketRouteRegistrationError',
    'InvalidSetting',
    'abort',
    'status'
)

def status(code: int):
    def decorator(cls):
        status_code = getattr(cls, 'status_code', None)

        if not status_code:
            status_code = code
            cls.status_code = status_code

        excs[status_code] = cls
        return cls
    return decorator

class AppError(Exception):
    """Base inheritance class for errors that occur during the Application's runtime."""
    pass

class BadConversion(AppError):
    pass


class HTTPException(Response, AppError):
    status_code = None

    def __init__(self, reason=None, content_type=None):
        self._reason = reason
        self._content_type = content_type
        
        Response.__init__(self,
                        body=self._reason,
                        status=self.status_code,
                        content_type=self._content_type or "text/plain")

        AppError.__init__(self, self._reason)

@status(404)
class NotFound(HTTPException):
    pass

@status(400)
class BadRequest(HTTPException):
    pass

@status(403)
class Forbidden(HTTPException):
    pass

@status(401)
class Unauthorized(HTTPException):
    pass


@status(302)
class Found(HTTPException):
    def __init__(self, location, reason=None, content_type=None):
        super().__init__(reason=reason, content_type=content_type)
        self.add_header("Location", location)

class EndpointError(AppError):
    pass

class EndpointLoadError(EndpointError):
    pass

class EndpointNotFound(EndpointError):
    pass

class ExtensionError(AppError):
    pass

class ExtensionLoadError(ExtensionError):
    pass

class ExtensionNotFound(ExtensionError):
    pass

class InvalidSetting(AppError):
    pass

class RegistrationError(AppError):
    pass        

class RouteRegistrationError(RegistrationError):
    pass

class WebsocketRouteRegistrationError(RegistrationError):
    pass


class ListenerRegistrationError(RegistrationError):
    pass

class MiddlewareRegistrationError(RegistrationError):
    pass

class ShardRegistrationError(RegistrationError):
    pass

class ViewRegistrationError(RegistrationError):
    pass


def abort(status_code: int, *, message: str=None, content_type: str='text/plain'):
    if not message:
        message, _ = responses.get(status_code)

    error = excs.get(status_code, HTTPException)
    return error(reason=message, content_type=content_type)

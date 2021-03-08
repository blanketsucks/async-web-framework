"""

exception hierarchy (this is the general one for all the framework not only this module):

AtomException:
    ApplicationError:
        BadConversion
        HTTPException:
            NotFound
            BadRequest
            Unauthorized
            Forbidden
        EndpointError:
            EndpointLoadError
            EndpointNotFound
        RegistrationError:
            RouteRegistrationError
            ListenerRegistrationError
            MiddlewareRegistrationError
            ShardRegistrationError
            ViewRegistrationError
            WebsocketRouteRegistrationError
        InvalidSetting
    ServerError:
        ConnectionError
    WebsocketError:
        InvalidHandshake
    MultipleValuesFound
    MissingHeader
    DatabaseError:
        NoConnections
    CLIException:
        CommandError:
            CommandInvokationError:
                FailedConversion
                MissingArgument
                MissingContextArgument

"""


from .response import Response, responses

excs = {}

__all__ = (
    'AtomException',
    'ApplicationError',
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

class AtomException(Exception):
    """Base inheritance class for errors that occur during the Application's runtime."""
    ...

class ApplicationError(Exception):
    ...

class BadConversion(ApplicationError):
    ...


class HTTPException(Response, ApplicationError):
    status_code = None

    def __init__(self, reason=None, content_type=None):
        self._reason = reason
        self._content_type = content_type
        
        Response.__init__(self,
                        body=self._reason,
                        status=self.status_code,
                        content_type=self._content_type or "text/plain")

        ApplicationError.__init__(self, self._reason)

@status(404)
class NotFound(HTTPException):
    ...

@status(400)
class BadRequest(HTTPException):
    ...

@status(403)
class Forbidden(HTTPException):
    ...

@status(401)
class Unauthorized(HTTPException):
    ...

@status(302)
class Found(HTTPException):
    def __init__(self, location, reason=None, content_type=None):
        super().__init__(reason=reason, content_type=content_type)
        self.add_header("Location", location)

class EndpointError(ApplicationError):
    ...

class EndpointLoadError(EndpointError):
    ...

class EndpointNotFound(EndpointError):
    ...

class ExtensionError(ApplicationError):
    ...

class ExtensionLoadError(ExtensionError):
    ...

class ExtensionNotFound(ExtensionError):
    ...

class InvalidSetting(ApplicationError):
    ...

class RegistrationError(ApplicationError):
    ...        

class RouteRegistrationError(RegistrationError):
    ...

class WebsocketRouteRegistrationError(RegistrationError):
    ...


class ListenerRegistrationError(RegistrationError):
    ...

class MiddlewareRegistrationError(RegistrationError):
    ...

class ShardRegistrationError(RegistrationError):
    ...

class ViewRegistrationError(RegistrationError):
    ...


def abort(status_code: int, *, message: str=None, content_type: str='text/plain'):
    if not message:
        message, _ = responses.get(status_code)

    error = excs.get(status_code, HTTPException)
    return error(reason=message, content_type=content_type)

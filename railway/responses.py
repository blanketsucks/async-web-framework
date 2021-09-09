"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from typing import Any, Dict, Type, Optional, TypeVar
from .response import Response, HTTPStatus

__all__ = (
    'HTTPException',
    'Continue',
    'SwitchingProtocols',
    'Processing',
    'EarlyHints',
    'OK',
    'Created',
    'Accepted',
    'NonAuthoritativeInformation',
    'NoContent',
    'ResetContent',
    'PartialContent',
    'MultiStatus',
    'AlreadyReported',
    'IMUsed',
    'MultipleChoice',
    'MovedPermanently',
    'Found',
    'SeeOther',
    'NotModified',
    'TemporaryRedirect',
    'PermanentRedirect',
    'BadRequest',
    'Unauthorized',
    'PaymentRequired',
    'Forbidden',
    'NotFound',
    'MethodNotAllowed',
    'NotAcceptable',
    'ProxyAuthenticationRequired',
    'RequestTimeout',
    'Conflict',
    'Gone',
    'LengthRequired',
    'PayloadTooLarge',
    'URITooLong',
    'UnsupportedMediaType',
    'RangeNotSatisfiable',
    'ExpectationFailed',
    'ImATeapot',
    'MisdirectedRequest',
    'UnprocessableEntity',
    'Locked',
    'FailedDependency',
    'TooEarly',
    'UpgradeRequired',
    'PreconditionRequired',
    'TooManyRequests',
    'RequestHeaderFieldsTooLarge',
    'UnavailableForLegalReasons',
    'InternalServerError',
    'NotImplemented',
    'BadGateway',
    'ServiceUnavailable',
    'GatewayTimeout',
    'HTTPVersionNotSupported',
    'VariantAlsoNegotiates',
    'InsufficientStorage',
    'LoopDetected',
    'NotExtended',
    'NetworkAuthenticationRequired',
    'abort',
    'informational_responses',
    'successful_responses',
    'redirects',
    'client_errors',
    'server_errors',
)

T = TypeVar('T')
responses: Dict[int, Type[Any]] = {}

def get(status: int):
    return responses.get(status)

def status(code: int):
    def decorator(cls: Type[T]) -> Type[T]:
        status = getattr(cls, '_status', None)

        if not status:
            status = code
            cls._status = status # type: ignore

        responses[status] = cls
        return cls

    return decorator

class HTTPResponse(Response):
    _status: Optional[int] = None

    def __init__(self, 
                body: Any=None, 
                content_type: Optional[str]=None, 
                headers: Optional[Dict[str, Any]]=None):
        Response.__init__(self, body, self._status, content_type, headers)

class HTTPException(HTTPResponse, Exception):
    def __init__(self, 
                reason: Optional[str]=None, 
                content_type: Optional[str]=None,
                headers: Optional[Dict[str, Any]]=None):
        self._reason = reason
        self._content_type = content_type

        HTTPResponse.__init__(self, body=self._reason, content_type=self._content_type, headers=headers)
        Exception.__init__(self, self._reason)

    def __repr__(self) -> str:
        return HTTPResponse.__repr__(self)

@status(100)
class Continue(HTTPResponse):
    """
    This interim response indicates that everything so far is OK and that the client should continue the request, 
    or ignore the response if the request is already finished.
    """

@status(101)
class SwitchingProtocols(HTTPResponse):
    """
    This code is sent in response to an `Upgrade` request header from the client, 
    and indicates the protocol the server is switching to.
    """

@status(102)
class Processing(HTTPResponse):
    """
    This code indicates that the server has received and is processing the request, but no response is available yet.
    """

@status(103)
class EarlyHints(HTTPResponse):
    """
    This status code is primarily intended to be used with the `Link` header, 
    letting the user agent start preloading resources while the server prepares a response.
    """

@status(200)
class OK(HTTPResponse):
    """
    The request has succeeded. The meaning of the success depends on the HTTP method:\n
        - `GET`: The resource has been fetched and is transmitted in the message body.\n
        - `HEAD`: The representation headers are included in the response without any message body.\n
        - `PUT` or `POST`: The resource describing the result of the action is transmitted in the message body.\n
        - `TRACE`: The message body contains the request message as received by the server.
    """

@status(201)
class Created(HTTPResponse):
    """
    The request has succeeded and a new resource has been created as a result. 
    This is typically the response sent after `POST` requests, or some `PUT` requests.
    """

@status(202)
class Accepted(HTTPResponse):
    """
    The request has been received but not yet acted upon. It is noncommittal, 
    since there is no way in HTTP to later send an asynchronous response indicating the outcome of the request. 
    It is intended for cases where another process or server handles the request, or for batch processing.
    """

@status(203)
class NonAuthoritativeInformation(HTTPResponse):
    """
    This response code means the returned meta-information is not exactly the same as is available from the origin server, 
    but is collected from a local or a third-party copy. This is mostly used for mirrors or backups of another resource. 
    Except for that specific case, the "200 OK" response is preferred to this status.
    """

@status(204)
class NoContent(HTTPResponse):
    """
    There is no content to send for this request, but the headers may be useful. 
    The user-agent may update its cached headers for this resource with the new ones.
    """

@status(205)
class ResetContent(HTTPResponse):
    """
    Tells the user-agent to reset the document which sent this request.
    """

@status(206)
class PartialContent(HTTPResponse):
    """
    This response code is used when the `Range` header is sent from the client to request only part of a resource.
    """

@status(207)
class MultiStatus(HTTPResponse):
    """
    Conveys information about multiple resources, for situations where multiple status codes might be appropriate.
    """

@status(208)
class AlreadyReported(HTTPResponse):
    """
    Used inside a `<dav:propstat>` response element to avoid repeatedly enumerating the internal members of multiple bindings to the same collection.
    """

@status(226)
class IMUsed(HTTPResponse):
    """
    The server has fulfilled a GET request for the resource,
    and the response is a representation of the result of one or more instance-manipulations applied to the current instance.
    """

class Redirection(HTTPResponse):
    def __init__(self, location: str, body: Any=None, content_type: Optional[str]=None, headers: Optional[Dict[str, Any]]=None):
        super().__init__(body=body, content_type=content_type, headers=headers)
        self.add_header("Location", location)

@status(300)
class MultipleChoice(Redirection):
    """
    The request has more than one possible response. The user-agent or user should choose one of them. 
    (There is no standardized way of choosing one of the responses, but HTML links to the possibilities are recommended so the user can pick.)
    """

@status(301)
class MovedPermanently(Redirection):
    """
    The URL of the requested resource has been changed permanently. The new URL is given in the response.
    """

@status(302)
class Found(Redirection):
    """
    This response code means that the URI of requested resource has been changed temporarily. Further changes in the URI might be made in the future. 
    Therefore, this same URI should be used by the client in future requests.
    """

@status(303)
class SeeOther(Redirection):
    """
    The server sent this response to direct the client to get the requested resource at another URI with a GET request.
    """

@status(304)
class NotModified(Redirection):
    """
    This is used for caching purposes. It tells the client that the response has not been modified, 
    so the client can continue to use the same cached version of the response.
    """
    
@status(307)
class TemporaryRedirect(Redirection):
    """
    The server sends this response to direct the client to get the requested resource at another URI with same method that was used in the prior request. 
    This has the same semantics as the `302 Found` HTTP response code, with the exception that the user agent must not change the HTTP method used: If a POST was used in the first request, 
    a `POST` must be used in the second request.
    """

@status(308)    
class PermanentRedirect(Redirection):
    """
    This means that the resource is now permanently located at another URI, specified by the Location: HTTP Response header. 
    This has the same semantics as the `301 Moved Permanently` HTTP response code, 
    with the exception that the user agent must not change the HTTP method used: If a `POST` was used in the first request, a `POST` must be used in the second request.
    """

@status(400)
class BadRequest(HTTPException):
    """
    The server could not understand the request due to invalid syntax.
    """

@status(401)
class Unauthorized(HTTPException):
    """
    Although the HTTP standard specifies "unauthorized", semantically this response means "unauthenticated". 
    That is, the client must authenticate itself to get the requested response.
    """

@status(402)
class PaymentRequired(HTTPException):
    """
    This response code is reserved for future use. The initial aim for creating this code was using it for digital payment systems, 
    however this status code is used very rarely and no standard convention exists.
    """

@status(403)
class Forbidden(HTTPException):
    """
    The client does not have access rights to the content; that is, it is unauthorized, 
    so the server is refusing to give the requested resource. Unlike `401`, the client's identity is known to the server.
    """

@status(404)
class NotFound(HTTPException):
    """
    The server can not find the requested resource. In the browser, this means the URL is not recognized. 
    In an API, this can also mean that the endpoint is valid but the resource itself does not exist. 
    Servers may also send this response instead of `403` to hide the existence of a resource from an unauthorized client. 
    This response code is probably the most famous one due to its frequent occurrence on the web.
    """

@status(405)
class MethodNotAllowed(HTTPException):
    """
    The request method is known by the server but is not supported by the target resource. 
    For example, an API may forbid DELETE-ing a resource.
    """

@status(406)
class NotAcceptable(HTTPException):
    """
    This response is sent when the web server, after performing (server-driven content negotiation)[https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation#server-driven_negotiation], 
    doesn't find any content that conforms to the criteria given by the user agent.
    """

@status(407)
class ProxyAuthenticationRequired(HTTPException):
    """
    This is similar to 401 but authentication is needed to be done by a proxy.
    """

@status(408)
class RequestTimeout(HTTPException):
    """
    This response is sent on an idle connection by some servers, even without any previous request by the client. 
    It means that the server would like to shut down this unused connection. 
    This response is used much more since some browsers, like Chrome, Firefox 27+, or IE9, use HTTP pre-connection mechanisms to speed up surfing. 
    Also note that some servers merely shut down the connection without sending this message.
    """

@status(409)
class Conflict(HTTPException):
    """
    This response is sent when a request conflicts with the current state of the server.
    """

@status(410)
class Gone(HTTPException):
    """
    This response is sent when the requested content has been permanently deleted from server, with no forwarding address. Clients are expected to remove their caches and links to the resource. 
    The HTTP specification intends this status code to be used for "limited-time, promotional services".
    APIs should not feel compelled to indicate resources that have been deleted with this status code.
    """

@status(411)
class LengthRequired(HTTPException):
    """
    Server rejected the request because the `Content-Length` header field is not defined and the server requires it.
    """

@status(412)
class PreconditionFailed(HTTPException):
    """
    The client has indicated preconditions in its headers which the server does not meet.
    """

@status(413)
class PayloadTooLarge(HTTPException):
    """
    Request entity is larger than limits defined by server; 
    the server might close the connection or return an `Retry-After` header field.
    """

@status(414)
class URITooLong(HTTPException):
    """
    The URI requested by the client is longer than the server is willing to interpret.
    """

@status(415)
class UnsupportedMediaType(HTTPException):
    """
    The media format of the requested data is not supported by the server, so the server is rejecting the request.
    """

@status(416)
class RangeNotSatisfiable(HTTPException):
    """
    The range specified by the `Range` header field in the request can't be fulfilled; 
    it's possible that the range is outside the size of the target URI's data.
    """

@status(417)
class ExpectationFailed(HTTPException):
    """
    This response code means the expectation indicated by the `Expect` request header field can't be met by the server.
    """

@status(418)
class ImATeapot(HTTPException):
    """
    The server refuses the attempt to brew coffee with a teapot.
    """

@status(421)
class MisdirectedRequest(HTTPException):
    """
    The request was directed at a server that is not able to produce a response. 
    This can be sent by a server that is not configured to produce responses for the combination of scheme and authority that are included in the request URI.
    """

@status(422)
class UnprocessableEntity(HTTPException):
    """
    The request was well-formed but was unable to be followed due to semantic errors.
    """

@status(423)
class Locked(HTTPException):
    """
    The resource that is being accessed is locked.
    """

@status(424)
class FailedDependency(HTTPException):
    """
    The request failed due to failure of a previous request.
    """

@status(425)
class TooEarly(HTTPException):
    """
    Indicates that the server is unwilling to risk processing a request that might be replayed.
    """

@status(426)
class UpgradeRequired(HTTPException):
    """
    The server refuses to perform the request using the current protocol but might be willing to do so after the client upgrades to a different protocol. 
    The server sends an `Upgrade` header in a `426 `response to indicate the required protocol(s).
    """

@status(428)
class PreconditionRequired(HTTPException):
    """
    The origin server requires the request to be conditional. This response is intended to prevent the 'lost update' problem, 
    where a client `GET`s a resource's state, modifies it, and `PUT`s it back to the server, 
    when meanwhile a third party has modified the state on the server, leading to a conflict.
    """

@status(429)
class TooManyRequests(HTTPException):
    """
    The user has sent too many requests in a given amount of time ("rate limiting").
    """

@status(431)
class RequestHeaderFieldsTooLarge(HTTPException):
    """
    The server is unwilling to process the request because its header fields are too large. 
    The request may be resubmitted after reducing the size of the request header fields.
    """

@status(451)
class UnavailableForLegalReasons(HTTPException):
    """
    The user-agent requested a resource that cannot legally be provided, such as a web page censored by a government.
    """

@status(500)
class InternalServerError(HTTPException):
    """
    The server has encountered a situation it doesn't know how to handle.
    """

@status(501)
class NotImplemented(HTTPException):
    """
    The request method is not supported by the server and cannot be handled. 
    The only methods that servers are required to support (and therefore that must not return this code) are `GET` and `HEAD`.
    """

@status(502)
class BadGateway(HTTPException):
    """
    This error response means that the server, 
    while working as a gateway to get a response needed to handle the request, got an invalid response.
    """

@status(503)
class ServiceUnavailable(HTTPException):
    """
    The server is not ready to handle the request. Common causes are a server that is down for maintenance or that is overloaded. 
    Note that together with this response, a user-friendly page explaining the problem should be sent. 
    This response should be used for temporary conditions and the `Retry-After`: HTTP header should, if possible, contain the estimated time before the recovery of the service. 
    The webmaster must also take care about the caching-related headers that are sent along with this response, as these temporary condition responses should usually not be cached.
    """

@status(504)
class GatewayTimeout(HTTPException):
    """
    This error response is given when the server is acting as a gateway and cannot get a response in time.
    """

@status(505)
class HTTPVersionNotSupported(HTTPException):
    """
    The HTTP version used in the request is not supported by the server.
    """

@status(506)
class VariantAlsoNegotiates(HTTPException):
    """
    The server has an internal configuration error: the chosen variant resource is configured to engage in transparent content negotiation itself, 
    and is therefore not a proper end point in the negotiation process.
    """

@status(507)
class InsufficientStorage(HTTPException):
    """
    The method could not be performed on the resource because the server is unable to store the representation needed to successfully complete the request.
    """

@status(508)
class LoopDetected(HTTPException):
    """
    The server detected an infinite loop while processing the request.
    """

@status(510)
class NotExtended(HTTPException):
    """
    Further extensions to the request are required for the server to fulfill it.
    """

@status(511)
class NetworkAuthenticationRequired(HTTPException):
    """
    Further extensions to the request are required for the server to fulfill it.
    """

def abort(_status: int, *, message: Optional[str]=None, content_type: str='text/html'):
    if not message:
        _status = HTTPStatus(_status) # type: ignore
        message = _status.description

        _status = _status.value

    if _status not in client_errors or _status not in server_errors:
        ret = f'{_status} is not a valid status code for both client errors and server errors'
        raise ValueError(ret)

    error = responses.get(_status, HTTPException)
    return error(reason=message, content_type=content_type)

informational_responses = {
    code: cls
    for code, cls in responses.items() if 100 <= code <= 199
}

successful_responses = {
    code: cls
    for code, cls in responses.items() if 200 <= code <= 299
}

redirects = {
    code: cls
    for code, cls in responses.items() if 300 <= code <= 399
}

client_errors = {
    code: cls
    for code, cls in responses.items() if 400 <= code <= 499
}

server_errors = {
    code: cls
    for code, cls in responses.items() if 500 <= code <= 599
}

.. currentmodule:: railway

.. |br| raw:: html

   <br />

API Reference
===============

Applications
------------------

Application
~~~~~~~~~~~~~~~~~~

.. autoclass:: Application
    :members:
    :exclude-members: event, route, resource, view, middleware, websocket, get, post, put, head, options, delete, patch

    .. automethod:: Application.event
        :decorator:

    .. automethod:: Application.route
        :decorator:

    .. automethod:: Application.get
        :decorator:

    .. automethod:: Application.put
        :decorator:

    .. automethod:: Application.post
        :decorator:

    .. automethod:: Application.delete
        :decorator:

    .. automethod:: Application.head
        :decorator:

    .. automethod:: Application.options
        :decorator:

    .. automethod:: Application.patch
        :decorator:

    .. automethod:: Application.websocket
        :decorator:

    .. automethod:: Application.resource
        :decorator:

    .. automethod:: Application.view
        :decorator:

    .. automethod:: Application.middleware
        :decorator:


IPv6 Applications
~~~~~~~~~~~~~~~~~~

For IPv6 applications, you can pass in ``ipv6=True`` into the :class:`~app.Appliaction` constructor
and an optional ``host`` argument which defaults to the local host if not given (in this case it is ::1).


Dual-Stack Applications
~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: dualstack_ipv6
    

Settings
-----------------------

Settings
~~~~~~~~~~~~~~~~~~

.. autoclass:: Settings
    :members:


Settings helpers
~~~~~~~~~~~~~~~~~~

.. autofunction:: settings_from_file
.. autofunction:: settings_from_env
    

Objects
-----------------------

Object
~~~~~~~~~~~~~~~~~~

.. autoclass:: Object
    :members:


PartialRoute
~~~~~~~~~~~~~~~~~~

.. autoclass:: PartialRoute
    :members:


Route
~~~~~~~~~~~~~~~~~~

.. autoclass:: Route
    :members:


WebsocketRoute
~~~~~~~~~~~~~~~~~~

.. autoclass:: WebsocketRoute
    :members:


Middleware
~~~~~~~~~~~~~~~~~~

.. autoclass:: Middleware
    :members:


Listener
~~~~~~~~~~~~~~~~~~

.. autoclass:: Listener
    :members:


Helper functions
~~~~~~~~~~~~~~~~~~

.. autofunction:: route
.. autofunction:: websocket_route
.. autofunction:: middleware
.. autofunction:: listener


Responses
-----------------------


HTTPStatus
~~~~~~~~~~~~

.. autoenum:: HTTPStatus

Response
~~~~~~~~~~~~~~~~~~

.. autoclass:: Response
    :members:


HTMLResponse
~~~~~~~~~~~~~~~~~~

.. autoclass:: HTMLResponse
    :members:
    :undoc-members:

JSONResponse
~~~~~~~~~~~~~~~~~~

.. autoclass:: JSONResponse
    :members:

FileResponse
~~~~~~~~~~~~~~~~~~

.. autoclass:: FileResponse
    :members:

The following classes and their descriptions are taken from https://developer.mozilla.org/en-US/docs/Web/HTTP/Status.


Continue
~~~~~~~~~~~~~~~~~~

.. autoclass:: Continue
    :members:


SwitchingProtocols
~~~~~~~~~~~~~~~~~~

.. autoclass:: SwitchingProtocols
    :members:


Processing
~~~~~~~~~~~~~~~~~~

.. autoclass:: Processing
    :members:


EarlyHints
~~~~~~~~~~~~~~~~~~

.. autoclass:: EarlyHints
    :members:


OK
~~~~~~~~~~~~~~~~~~

.. autoclass:: OK
    :members:


Created
~~~~~~~~~~~~~~~~~~

.. autoclass:: Created
    :members:


Accepted
~~~~~~~~~~~~~~~~~~

.. autoclass:: Accepted
    :members:


NonAuthoritativeInformation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: NonAuthoritativeInformation
    :members:


NoContent
~~~~~~~~~~~~~~~~~~

.. autoclass:: NoContent
    :members:


ResetContent
~~~~~~~~~~~~~~~~~~

.. autoclass:: ResetContent
    :members:


PartialContent
~~~~~~~~~~~~~~~~~~

.. autoclass:: PartialContent
    :members:


MultiStatus
~~~~~~~~~~~~~~~~~~

.. autoclass:: MultiStatus
    :members:


AlreadyReported
~~~~~~~~~~~~~~~~~~

.. autoclass:: AlreadyReported
    :members:


IMUsed
~~~~~~~~~~~~~~~~~~

.. autoclass:: IMUsed
    :members:


MultipleChoice
~~~~~~~~~~~~~~~~~~

.. autoclass:: MultipleChoice
    :members:


MovedPermanently
~~~~~~~~~~~~~~~~~~

.. autoclass:: MovedPermanently
    :members:


Found
~~~~~~~~~~~~~~~~~~

.. autoclass:: Found
    :members:


SeeOther
~~~~~~~~~~~~~~~~~~

.. autoclass:: SeeOther
    :members:


NotModified
~~~~~~~~~~~~~~~~~~

.. autoclass:: NotModified
    :members:


TemporaryRedirect
~~~~~~~~~~~~~~~~~~

.. autoclass:: TemporaryRedirect
    :members:


PermanentRedirect
~~~~~~~~~~~~~~~~~~

.. autoclass:: PermanentRedirect
    :members:


BadRequest
~~~~~~~~~~~~~~~~~~

.. autoclass:: BadRequest
    :members:


Unauthorized
~~~~~~~~~~~~~~~~~~

.. autoclass:: Unauthorized
    :members:


PaymentRequired
~~~~~~~~~~~~~~~~~~

.. autoclass:: PaymentRequired
    :members:


Forbidden
~~~~~~~~~~~~~~~~~~

.. autoclass:: Forbidden
    :members:


NotFound
~~~~~~~~~~~~~~~~~~

.. autoclass:: EarlyHints
    :members:


MethodNotAllowed
~~~~~~~~~~~~~~~~~~

.. autoclass:: MethodNotAllowed
    :members:


NotAcceptable
~~~~~~~~~~~~~~~~~~

.. autoclass:: NotAcceptable
    :members:


ProxyAuthenticationRequired
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ProxyAuthenticationRequired
    :members:


RequestTimeout
~~~~~~~~~~~~~~~~~~

.. autoclass:: RequestTimeout
    :members:


Conflict
~~~~~~~~~~~~~~~~~~

.. autoclass:: Conflict
    :members:


Gone
~~~~~~~~~~~~~~~~~~

.. autoclass:: Gone
    :members:


LengthRequired
~~~~~~~~~~~~~~~~~~

.. autoclass:: LengthRequired
    :members:


PayloadTooLarge
~~~~~~~~~~~~~~~~~~

.. autoclass:: PayloadTooLarge
    :members:


URITooLong
~~~~~~~~~~~~~~~~~~

.. autoclass:: URITooLong
    :members:


UnsupportedMediaType
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: UnsupportedMediaType
    :members:


RangeNotSatisfiable
~~~~~~~~~~~~~~~~~~~

.. autoclass:: RangeNotSatisfiable
    :members:


ExpectationFailed
~~~~~~~~~~~~~~~~~~

.. autoclass:: ExpectationFailed
    :members:


ImATeapot
~~~~~~~~~~~~~~~~~~

.. autoclass:: ImATeapot
    :members:


MisdirectedRequest
~~~~~~~~~~~~~~~~~~~

.. autoclass:: MisdirectedRequest
    :members:


UnprocessableEntity
~~~~~~~~~~~~~~~~~~~

.. autoclass:: UnprocessableEntity
    :members:


Locked
~~~~~~~~~~~~~~~~~~

.. autoclass:: Locked
    :members:


FailedDependency
~~~~~~~~~~~~~~~~~~

.. autoclass:: FailedDependency
    :members:


TooEarly
~~~~~~~~~~~~~~~~~~

.. autoclass:: TooEarly
    :members:


UpgradeRequired
~~~~~~~~~~~~~~~~~~

.. autoclass:: UpgradeRequired
    :members:


PreconditionRequired
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: PreconditionRequired
    :members:


TooManyRequests
~~~~~~~~~~~~~~~~~~

.. autoclass:: TooManyRequests
    :members:


RequestHeaderFieldsTooLarge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: RequestHeaderFieldsTooLarge
    :members:


UnavailableForLegalReasons
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: UnavailableForLegalReasons
    :members:


InternalServerError
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: InternalServerError
    :members:


NotImplemented
~~~~~~~~~~~~~~~~~~

.. autoclass:: NotImplemented
    :members:


BadGateway
~~~~~~~~~~~~~~~~~~

.. autoclass:: BadGateway
    :members:


ServiceUnavailable
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ServiceUnavailable
    :members:


GatewayTimeout
~~~~~~~~~~~~~~~~~~

.. autoclass:: GatewayTimeout
    :members:


HTTPVersionNotSupported
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: HTTPVersionNotSupported
    :members:


VariantAlsoNegotiates
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: VariantAlsoNegotiates
    :members:


InsufficientStorage
~~~~~~~~~~~~~~~~~~~

.. autoclass:: InsufficientStorage
    :members:


LoopDetected
~~~~~~~~~~~~~~~~~~

.. autoclass:: LoopDetected
    :members:


NotExtended
~~~~~~~~~~~~~~~~~~

.. autoclass:: NotExtended
    :members:


NetworkAuthenticationRequired
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: NetworkAuthenticationRequired
    :members:

Requests
--------------------

Request
~~~~~~~~

.. autoclass:: Request
    :members:


Form-Data
--------------------

Disposition
~~~~~~~~~~~~

.. autoclass:: Disposition
    :members:


FormData
~~~~~~~~~

.. autoclass:: FormData
    :members:


Cookies
--------------------

CookieJar
~~~~~~~~~~

.. autoclass:: CookieJar
    :members:

Cookie
~~~~~~~~~~

.. autoclass:: Cookie
    :members:

Files
-----------------

File
~~~~~~~~~~~~~~~~~~

.. autoclass:: File
    :members:
    :exclude-members: stream

    .. automethod:: File.stream
        :async-for:


Data Structures
--------------------

ImmutableMapping
~~~~~~~~~~~~~~~~~~

.. autoclass:: ImmutableMapping
    :members:

MultiDict
~~~~~~~~~~~~~~~~~~

.. autoclass:: MultiDict
    :members:

URL
~~~~~~~~~~~~~~~~~~

.. autoclass:: URL
    :members:


Views
--------------------

ViewMeta
~~~~~~~~~~~~~~~~~~

.. autoclass:: ViewMeta
    :members:


HTTPView
~~~~~~~~~~~~~~~~~~

.. autoclass:: HTTPView
    :members:


Injectables
--------------------------

InjectableMeta
~~~~~~~~~~~~~~~~~~

.. autoclass:: InjectableMeta
    :members:

Injectable
~~~~~~~~~~~~~~~~~~

.. autoclass:: Injectable
    :members:

Resources
-----------

ResourceMeta
~~~~~~~~~~~~~

.. autoclass:: ResourceMeta
    :members:

Resource
~~~~~~~~~~

.. autoclass:: Resource
    :members:


Models
---------------------

Field
~~~~~~~~~~~~~~~~~~

.. autoclass:: Field
    :members:

ModelMeta
~~~~~~~~~~~~~~~~~~

.. autoclass:: ModelMeta
    :members:

Model
~~~~~~~~~~~~~~~~~~

.. autoclass:: Model
    :members:

Routers
---------------------

Router
~~~~~~~~~~

.. autoclass:: Router
    :members:
    :exclude-members: route, middleware, websocket, get, post, put, head, options, delete, patch

    .. automethod:: Router.route
        :decorator:

    .. automethod:: Router.get
        :decorator:

    .. automethod:: Router.put
        :decorator:

    .. automethod:: Router.post
        :decorator:

    .. automethod:: Router.delete
        :decorator:

    .. automethod:: Router.head
        :decorator:

    .. automethod:: Router.options
        :decorator:

    .. automethod:: Router.patch
        :decorator:

    .. automethod:: Router.websocket
        :decorator:

    .. automethod:: Router.middleware
        :decorator:

Ratelimits
--------------

RatelimitHandler
~~~~~~~~~~~~~~~~~

.. autoclass:: RatelimitHandler
    :members:

Bucket
~~~~~~~~~

.. autoclass:: Bucket
    :members:

Key
~~~~

.. autoclass:: Key
    :members:

Sessions
---------

CookieSession
~~~~~~~~~~~~~~~

.. autoclass:: CookieSession
    :members:

Templates
----------

TemplateContext
~~~~~~~~~~~~~~~~

.. autoclass:: TemplateContext
    :members:

Template
~~~~~~~~~

.. autoclass:: Template
    :members:

.. autofunction:: render

Workers
--------

Worker
~~~~~~~

.. autoclass:: Worker
    :members:

Locks
------

Semaphore
~~~~~~~~~~

.. autoclass:: Semaphore
    :members:

Lock
~~~~~

.. autoclass:: Lock
    :members:

Streams
---------

StreamReader
~~~~~~~~~~~~

.. autoclass:: StreamReader
    :members:

StreamWriter
~~~~~~~~~~~~~

.. autoclass:: StreamWriter
    :members:

StreamTransport
~~~~~~~~~~~~~~~~

.. autoclass:: StreamTransport
    :members:

Utility functions
--------------------

.. autofunction:: maybe_coroutine
.. autofunction:: has_dualstack_ipv6
.. autofunction:: has_ipv6
.. autofunction:: is_ipv6
.. autofunction:: is_ipv4
.. autofunction:: validate_ip
.. autofunction:: jsonify

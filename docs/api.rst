.. currentmodule:: subway

API Reference
===============

URL
~~~~~~~~~~~~~~~~~~

.. autoclass:: URL
    :members:

Applications
------------------

BaseApplication
~~~~~~~~~~~~~~~~~

.. autoclass:: BaseApplication
    :members:
    :show-inheritance:
    :exclude-members: route, get, put, post, delete, head, options, patch, websocket, event

    .. automethod:: route
        :decorator:

    .. automethod:: get
        :decorator:

    .. automethod:: put
        :decorator:

    .. automethod:: post
        :decorator:

    .. automethod:: delete
        :decorator:

    .. automethod:: head
        :decorator:

    .. automethod:: options
        :decorator:

    .. automethod:: patch
        :decorator:

    .. automethod:: websocket
        :decorator:

    .. automethod:: event
        :decorator:

Application
~~~~~~~~~~~~~~~~~~

.. autoclass:: Application
    :members:
    :exclude-members: event, resource, view, status_code_handler

    .. automethod:: Application.event
        :decorator:

    .. automethod:: Application.resource
        :decorator:

    .. automethod:: Application.view
        :decorator:

    .. automethod:: Application.status_code_handler
        :decorator:


IPv6 Applications
~~~~~~~~~~~~~~~~~~

For IPv6 applications, you can pass in ``ipv6=True`` into the :class:`~.Appliaction` constructor
and an optional ``host`` argument which defaults to the local host if not given (in this case it is ::1).

Blueprints
~~~~~~~~~~~~

.. autoclass:: Blueprint
    :members:


Event Reference
-----------------

This section is all the events that are dispatches within the application's runtime.
Of course, you can dispatch your own events using :meth:`~.Application.dispatch`.

.. function:: on_startup()

    This event is called when the application has finished starting up and is ready to handle requests.

.. function:: on_worker_startup(worker)

    This event is like :func:`on_startup` but is called for each worker.

    :param worker: The worker that has just started.
    :type worker: :class:`~.Worker`

.. function:: on_shutdown()

    Called whenever the application has shutdown and finished background cleanup.

.. function:: on_worker_shutdown(worker)

    Called whenever a worker has finished shutting down.

    :param worker: The worker that has just shutdown.
    :type worker: :class:`~.Worker`

.. function:: on_request(request, worker)

    Called whenever a request is received.

    :param request: The request that has just been received.
    :type request: :class:`~.Request`
    :param worker: The worker that recevied the request.
    :type worker: :class:`~.Worker`


.. function:: on_error(route, request, error)

    Called whenever an error occurs during the request handling process.

    :param route: The route that was being handled.
    :type route: Union[:class:`~.PartialRoute`, :class:`~.Route`]
    :param request: The request that was being handled.
    :type request: :class:`~.Request`
    :param error: The error that was raised.
    :type error: :exc:`Exception`

.. function:: on_event_error(listener, error)

    Called whenever an error occrus within an event listener during dispatch.

    :param listener: The listener that was being dispatched.
    :type listener: :class:`~.Listener`
    :param error: The error that was raised.
    :type error: :exc:`Exception`

Test Client
------------

TestClient
~~~~~~~~~~~~

.. autoclass:: TestClient
    :members:


Routers
---------------------


Router
~~~~~~~~~~

.. autoclass:: Router
    :members:
    :exclude-members: route, websocket

    .. automethod:: Router.route
        :decorator:

    .. automethod:: Router.websocket
        :decorator:

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
    

Responses
-----------------------

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

Status Code Responses
------------------------

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

.. autoexception:: BadRequest
    :members:


Unauthorized
~~~~~~~~~~~~~~~~~~

.. autoexception:: Unauthorized
    :members:


PaymentRequired
~~~~~~~~~~~~~~~~~~

.. autoexception:: PaymentRequired
    :members:


Forbidden
~~~~~~~~~~~~~~~~~~

.. autoexception:: Forbidden
    :members:


NotFound
~~~~~~~~~~~~~~~~~~

.. autoexception:: EarlyHints
    :members:


MethodNotAllowed
~~~~~~~~~~~~~~~~~~

.. autoexception:: MethodNotAllowed
    :members:


NotAcceptable
~~~~~~~~~~~~~~~~~~

.. autoexception:: NotAcceptable
    :members:


ProxyAuthenticationRequired
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: ProxyAuthenticationRequired
    :members:


RequestTimeout
~~~~~~~~~~~~~~~~~~

.. autoexception:: RequestTimeout
    :members:


Conflict
~~~~~~~~~~~~~~~~~~

.. autoexception:: Conflict
    :members:


Gone
~~~~~~~~~~~~~~~~~~

.. autoexception:: Gone
    :members:


LengthRequired
~~~~~~~~~~~~~~~~~~

.. autoexception:: LengthRequired
    :members:


PayloadTooLarge
~~~~~~~~~~~~~~~~~~

.. autoexception:: PayloadTooLarge
    :members:


URITooLong
~~~~~~~~~~~~~~~~~~

.. autoexception:: URITooLong
    :members:


UnsupportedMediaType
~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: UnsupportedMediaType
    :members:


RangeNotSatisfiable
~~~~~~~~~~~~~~~~~~~

.. autoexception:: RangeNotSatisfiable
    :members:


ExpectationFailed
~~~~~~~~~~~~~~~~~~

.. autoexception:: ExpectationFailed
    :members:


ImATeapot
~~~~~~~~~~~~~~~~~~

.. autoexception:: ImATeapot
    :members:


MisdirectedRequest
~~~~~~~~~~~~~~~~~~~

.. autoexception:: MisdirectedRequest
    :members:


UnprocessableEntity
~~~~~~~~~~~~~~~~~~~

.. autoexception:: UnprocessableEntity
    :members:


Locked
~~~~~~~~~~~~~~~~~~

.. autoexception:: Locked
    :members:


FailedDependency
~~~~~~~~~~~~~~~~~~

.. autoexception:: FailedDependency
    :members:


TooEarly
~~~~~~~~~~~~~~~~~~

.. autoexception:: TooEarly
    :members:


UpgradeRequired
~~~~~~~~~~~~~~~~~~

.. autoexception:: UpgradeRequired
    :members:


PreconditionRequired
~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: PreconditionRequired
    :members:


TooManyRequests
~~~~~~~~~~~~~~~~~~

.. autoexception:: TooManyRequests
    :members:


RequestHeaderFieldsTooLarge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: RequestHeaderFieldsTooLarge
    :members:


UnavailableForLegalReasons
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: UnavailableForLegalReasons
    :members:


InternalServerError
~~~~~~~~~~~~~~~~~~~~

.. autoexception:: InternalServerError
    :members:


NotImplemented
~~~~~~~~~~~~~~~~~~

.. autoexception:: NotImplemented
    :members:


BadGateway
~~~~~~~~~~~~~~~~~~

.. autoexception:: BadGateway
    :members:


ServiceUnavailable
~~~~~~~~~~~~~~~~~~~~

.. autoexception:: ServiceUnavailable
    :members:


GatewayTimeout
~~~~~~~~~~~~~~~~~~

.. autoexception:: GatewayTimeout
    :members:


HTTPVersionNotSupported
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: HTTPVersionNotSupported
    :members:



VariantAlsoNegotiates
~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: VariantAlsoNegotiates
    :members:


InsufficientStorage
~~~~~~~~~~~~~~~~~~~

.. autoexception:: InsufficientStorage
    :members:


LoopDetected
~~~~~~~~~~~~~~~~~~

.. autoexception:: LoopDetected
    :members:


NotExtended
~~~~~~~~~~~~~~~~~~

.. autoexception:: NotExtended
    :members:


NetworkAuthenticationRequired
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: NetworkAuthenticationRequired
    :members:

Requests
--------------------

Request
~~~~~~~~

.. autoclass:: Request
    :members:


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
    :exclude-members: status_code_handler, on_error, middleware

    .. automethod:: Route.middleware
        :decorator:

    .. automethod:: Route.on_error
        :decorator:

    .. automethod:: Route.status_code_handler
        :decorator:


WebSocketRoute
~~~~~~~~~~~~~~~~~~

.. autoclass:: WebSocketRoute
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


Sessions
---------

CookieSession
~~~~~~~~~~~~~~~

.. autoclass:: CookieSession
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


Form-Data
--------------------

FormDataField
~~~~~~~~~~~~~~~~

.. autoclass:: FormDataField
    :members:

Disposition
~~~~~~~~~~~~

.. autoclass:: Disposition
    :members:


FormData
~~~~~~~~~

.. autoclass:: FormData
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

.. autoclass:: models.Field
    :members:

ModelMeta
~~~~~~~~~~~~~~~~~~

.. autoclass:: models.ModelMeta
    :members:

Model
~~~~~~~~~~~~~~~~~~

.. autoclass:: models.Model
    :members:
    :special-members: __setattr__, __iter__, __eq__


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

.. autoclass:: subway.streams.StreamReader
    :members:

StreamWriter
~~~~~~~~~~~~~

.. autoclass:: subway.streams.StreamWriter
    :members:

.. autofunction:: subway.streams.open_connection
.. autofunction:: subway.streams.start_server
.. autofunction:: subway.streams.start_unix_server

Utility functions
--------------------

.. autofunction:: maybe_coroutine
.. autofunction:: has_dualstack_ipv6
.. autofunction:: has_ipv6
.. autofunction:: is_ipv6
.. autofunction:: is_ipv4
.. autofunction:: validate_ip
.. autofunction:: socket_is_closed
.. autofunction:: jsonify
.. autofunction:: to_url
.. autofunction:: listdir
.. autofunction:: clean_values
.. autofunction:: unwrap_function
.. autofunction:: iscoroutinefunction
.. autofunction:: isasyncgenfunction
.. autofunction:: add_signal_handler
.. autofunction:: get_union_args
.. autofunction:: get_charset
.. autofunction:: copy_docstring
.. autofunction:: clear_docstring

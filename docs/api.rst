.. currentmodule:: railway

.. |br| raw:: html

   <br />

API Reference
===============

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

Applications
------------------

Application
~~~~~~~~~~~~~~~~~~

.. autoclass:: Application

    :members:
    :exclude-members: event, route, resource, view, middleware, websocket, get, post, put, head, options, delete, patch, status_code_handler

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

    .. automethod:: Application.status_code_handler
        :decorator:


IPv6 Applications
~~~~~~~~~~~~~~~~~~

For IPv6 applications, you can pass in ``ipv6=True`` into the :class:`~app.Appliaction` constructor
and an optional ``host`` argument which defaults to the local host if not given (in this case it is ::1).


Dual-Stack Applications
~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: dualstack_ipv6


Event Reference
-----------------

This section is all the events that are dispatches within the application's runtime.
Of course, you can dispatch your own events using :meth:`.Application.dispatch`.

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

.. function:: on_raw_request(data, worker)

    Called whenever a request is received.

    :param data: The request data.
    :type data: :class:`bytes`
    :param worker: The worker that received the data.
    :type worker: :class:`~.Worker`


.. function:: on_request(request, worker)

    Called whenever a request is received.

    :param request: The request that has just been received.
    :type request: :class:`~.Request`
    :param worker: The worker that recevied the request.
    :type worker: :class:`~.Worker`


.. function:: on_websocket_data_receive(data, worker)

    Called whenever websocket data is received.

    :param data: The data that has just been received.
    :type data: :class:`bytes`
    :param worker: The worker that received the data.
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
    :exclude-members: stream

    .. automethod:: File.stream
        :async-for:

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
    :special-members: __setattr__, __iter__, __eq__


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

Templates
----------

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


Extensions 
------------

ngrok
~~~~~~~

.. autoclass:: railway.extensions.ngrok.Application
    :members:

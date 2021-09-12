.. currentmodule:: railway

.. |br| raw:: html

   <br />

Applications
------------------

Application
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.app.Application
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

For IPv6 applications, you can pass in ``ipv6=True`` into the :class:`~railway.app.Appliaction` constructor
and an optional ``host`` argument which defaults to the local host if not given (in this case it is ::1).


Dual-Stack Applications
~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: railway.app.dualstack_ipv6
    

Settings
-----------------------

Settings
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.settings.Settings
    :members:


Settings helpers
~~~~~~~~~~~~~~~~~~

.. autofunction:: railway.settings.settings_from_file
.. autofunction:: railway.settings.settings_from_env
    

Objects
-----------------------

Object
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.objects.Object
    :members:


PartialRoute
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.objects.PartialRoute
    :members:


Route
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.objects.Route
    :members:


WebsocketRoute
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.objects.WebsocketRoute
    :members:


Middleware
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.objects.Middleware
    :members:


Listener
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.objects.Listener
    :members:


Helper functions
~~~~~~~~~~~~~~~~~~

.. autofunction:: railway.objects.route
.. autofunction:: railway.objects.websocket_route
.. autofunction:: railway.objects.middleware
.. autofunction:: railway.objects.listener


Responses
-----------------------

Response
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.response.Response
    :members:


HTMLResponse
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.response.HTMLResponse
    :members:


JSONResponse
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.response.JSONResponse
    :members:

FileResponse
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.response.FileResponse
    :members:

The following classes and their descriptions are taken from https://developer.mozilla.org/en-US/docs/Web/HTTP/Status.


Continue
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Continue
    :members:


SwitchingProtocols
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.SwitchingProtocols
    :members:


Processing
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Processing
    :members:


EarlyHints
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.EarlyHints
    :members:


OK
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.OK
    :members:


Created
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Created
    :members:


Accepted
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Accepted
    :members:


NonAuthoritativeInformation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.NonAuthoritativeInformation
    :members:


NoContent
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.NoContent
    :members:


ResetContent
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.ResetContent
    :members:


PartialContent
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.PartialContent
    :members:


MultiStatus
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.MultiStatus
    :members:


AlreadyReported
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.AlreadyReported
    :members:


IMUsed
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.IMUsed
    :members:


MultipleChoice
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.MultipleChoice
    :members:


MovedPermanently
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.MovedPermanently
    :members:


Found
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Found
    :members:


SeeOther
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.SeeOther
    :members:


NotModified
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.NotModified
    :members:


TemporaryRedirect
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.TemporaryRedirect
    :members:


PermanentRedirect
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.PermanentRedirect
    :members:


BadRequest
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.BadRequest
    :members:


Unauthorized
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Unauthorized
    :members:


PaymentRequired
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.PaymentRequired
    :members:


Forbidden
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Forbidden
    :members:


NotFound
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.EarlyHints
    :members:


MethodNotAllowed
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.MethodNotAllowed
    :members:


NotAcceptable
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.NotAcceptable
    :members:


ProxyAuthenticationRequired
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.ProxyAuthenticationRequired
    :members:


RequestTimeout
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.RequestTimeout
    :members:


Conflict
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Conflict
    :members:


Gone
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Gone
    :members:


LengthRequired
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.LengthRequired
    :members:


PayloadTooLarge
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.PayloadTooLarge
    :members:


URITooLong
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.URITooLong
    :members:


UnsupportedMediaType
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.UnsupportedMediaType
    :members:


RangeNotSatisfiable
~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.RangeNotSatisfiable
    :members:


ExpectationFailed
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.ExpectationFailed
    :members:


ImATeapot
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.ImATeapot
    :members:


MisdirectedRequest
~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.MisdirectedRequest
    :members:


UnprocessableEntity
~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.UnprocessableEntity
    :members:


Locked
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.Locked
    :members:


FailedDependency
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.FailedDependency
    :members:


TooEarly
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.TooEarly
    :members:


UpgradeRequired
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.UpgradeRequired
    :members:


PreconditionRequired
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.PreconditionRequired
    :members:


TooManyRequests
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.TooManyRequests
    :members:


RequestHeaderFieldsTooLarge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.RequestHeaderFieldsTooLarge
    :members:


UnavailableForLegalReasons
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.UnavailableForLegalReasons
    :members:


InternalServerError
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.InternalServerError
    :members:


NotImplemented
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.NotImplemented
    :members:


BadGateway
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.BadGateway
    :members:


ServiceUnavailable
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.ServiceUnavailable
    :members:


GatewayTimeout
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.GatewayTimeout
    :members:


HTTPVersionNotSupported
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.HTTPVersionNotSupported
    :members:


VariantAlsoNegotiates
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.VariantAlsoNegotiates
    :members:


InsufficientStorage
~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.InsufficientStorage
    :members:


LoopDetected
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.LoopDetected
    :members:


NotExtended
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.NotExtended
    :members:


NetworkAuthenticationRequired
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.responses.NetworkAuthenticationRequired
    :members:

Requests
--------------------

Request
~~~~~~~~

.. autoclass:: railway.request.Request
    :members:


Form-Data
--------------------

Disposition
~~~~~~~~~~~~

.. autoclass:: railway.formdata.Disposition
    :members:


FormData
~~~~~~~~~

.. autoclass:: railway.formdata.FormData
    :members:


Cookies
--------------------

CookieJar
~~~~~~~~~~

.. autoclass:: railway.cookies.CookieJar
    :members:

Cookie
~~~~~~~~~~

.. autoclass:: railway.cookies.Cookie
    :members:

Files
-----------------

File
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.file.File
    :members:
    :exclude-members: stream

    .. automethod:: File.stream
        :async-for:


Data Structures
--------------------

ImmutableMapping
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.datastructures.ImmutableMapping
    :members:
    :exclude-members: clear, copy, pop, popitem, setdefault, update

MultiDict
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.datastructures.MultiDict
    :members:
    :exclude-members: clear


URL
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.datastructures.URL
    :members:


Views
--------------------

ViewMeta
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.views.ViewMeta
    :members:


HTTPView
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.views.HTTPView
    :members:


Injectables
--------------------------

InjectableMeta
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.injectables.InjectableMeta
    :members:

Injectable
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.injectables.Injectable
    :members:

Resources
-----------

ResourceMeta
~~~~~~~~~~~~~

.. autoclass:: railway.resources.ResourceMeta
    :members:

Resource
~~~~~~~~~~

.. autoclass:: railway.resources.Resource
    :members:


Models
---------------------

Field
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.models.Field
    :members:

ModelMeta
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.models.ModelMeta
    :members:

Model
~~~~~~~~~~~~~~~~~~

.. autoclass:: railway.models.Model
    :members:

Routers
---------------------

Router
~~~~~~~~~~

.. autoclass:: railway.router.Router
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

.. autoclass:: railway.ratelimits.RatelimitHandler
    :members:

Bucket
~~~~~~~~~

.. autoclass:: railway.ratelimits.Bucket
    :members:

Key
~~~~

.. autoclass:: railway.ratelimits.Key
    :members:

Sessions
---------

CookieSession
~~~~~~~~~~~~~~~

.. autoclass:: railway.sessions.CookieSession
    :members:

Templates
----------

TemplateContext
~~~~~~~~~~~~~~~~

.. autoclass:: railway.templates.TemplateContext
    :members:

Template
~~~~~~~~~

.. autoclass:: railway.templates.Template
    :members:

.. autofunction:: railway.templates.render

Workers
--------

Worker
~~~~~~~

.. autoclass:: railway.workers.Worker
    :members:

Utility functions
--------------------

.. autofunction:: railway.utils.maybe_coroutine
.. autofunction:: railway.utils.has_dualstack_ipv6
.. autofunction:: railway.utils.has_ipv6
.. autofunction:: railway.utils.is_ipv6
.. autofunction:: railway.utils.is_ipv4
.. autofunction:: railway.utils.validate_ip
.. autofunction:: railway.utils.jsonify

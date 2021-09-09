.. currentmodule:: railway

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
and an optional ``host`` argument which defaults to the local host if not given (in this case it is '::1').

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


Models
---------------------

.. automodule:: railway.models
   :members:
   :show-inheritance:


Utility functions
--------------------

.. autoclass:: railway.utils.AsyncResource
    :members:

.. autofunction:: railway.utils.maybe_coroutine
.. autofunction:: railway.utils.has_ipv6
.. autofunction:: railway.utils.is_ipv6
.. autofunction:: railway.utils.is_ipv4
.. autofunction:: railway.utils.validate_ip

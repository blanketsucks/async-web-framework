.. currentmodule:: railway.websockets

Websockets API Documentation
=============================

Enums
------

WebsocketState
~~~~~~~~~~~~~~~

.. autoclass:: WebsocketState

    .. autoattribute:: CONNECTING
    .. autoattribute:: OPEN
    .. autoattribute:: SENDING
    .. autoattribute:: RECEIVING
    .. autoattribute:: CLOSING
    .. autoattribute:: CLOSED
    

WebsocketOpCode
~~~~~~~~~~~~~~~~~

.. autoclass:: WebsocketOpcode

    .. autoattribute:: CONTINUATION
    .. autoattribute:: TEXT
    .. autoattribute:: BINARY
    .. autoattribute:: CLOSE
    .. autoattribute:: PING
    .. autoattribute:: PONG

WebsocketCloseCode
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: WebsocketCloseCode
    
    .. autoattribute:: NORMAL
    .. autoattribute:: GOING_AWAY
    .. autoattribute:: PROTOCOL_ERROR
    .. autoattribute:: UNSUPPORTED_PAYLOAD
    .. autoattribute:: RESERVED
    .. autoattribute:: NO_STATUS
    .. autoattribute:: ABNORMAL
    .. autoattribute:: POLICY_VIOLATION
    .. autoattribute:: TOO_LARGE
    .. autoattribute:: MANDATORY_EXTENSION
    .. autoattribute:: INTERNAL_ERROR
    .. autoattribute:: SERVICE_RESTART
    .. autoattribute:: TRY_AGAIN_LATER
    .. autoattribute:: BAD_GATEWAY
    .. autoattribute:: TLS_HANDSHAKE


Websockets
------------

ServerWebsocket
~~~~~~~~~~~~~~~~

.. autoclass:: ServerWebsocket
    :members:

ClientWebsocket
~~~~~~~~~~~~~~~~

.. autoclass:: ClientWebsocket
    :members:

Frames
-------

Data
~~~~~~

.. autoclass:: Data
    :members:

WebsocketFrame
~~~~~~~~~~~~~~~

.. autoclass:: WebsocketFrame
    :members:



Errors
-------

.. autoexception:: WebsocketError
    :members:
    :show-inheritance:

Websocket Frame Errors
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: InvalidWebsocketFrame
    :members:
    :show-inheritance:

.. autoexception:: InvalidWebsocketOpcode
    :members:
    :show-inheritance:

.. autoexception:: InvalidWebsocketCloseCode
    :members:
    :show-inheritance:

Websocket Control Frame Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: InvalidWebsocketControlFrame
    :members:
    :show-inheritance:

.. autoexception:: FragmentedControlFrame
    :members:
    :show-inheritance:

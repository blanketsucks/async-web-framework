.. currentmodule:: railway.websockets

WebSockets API Documentation
=============================

Enums
------

WebSocketState
~~~~~~~~~~~~~~~

.. autoclass:: WebSocketState

    .. autoattribute:: CONNECTING
    .. autoattribute:: OPEN
    .. autoattribute:: SENDING
    .. autoattribute:: RECEIVING
    .. autoattribute:: CLOSING
    .. autoattribute:: CLOSED
    

WebSocketOpCode
~~~~~~~~~~~~~~~~~

.. autoclass:: WebSocketOpcode

    .. autoattribute:: CONTINUATION
    .. autoattribute:: TEXT
    .. autoattribute:: BINARY
    .. autoattribute:: CLOSE
    .. autoattribute:: PING
    .. autoattribute:: PONG

WebSocketCloseCode
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: WebSocketCloseCode
    
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


WebSockets
------------

ServerWebSocket
~~~~~~~~~~~~~~~~

.. autoclass:: ServerWebSocket
    :members:

ClientWebSocket
~~~~~~~~~~~~~~~~

.. autoclass:: ClientWebSocket
    :members:

Frames
-------

Data
~~~~~~

.. autoclass:: Data
    :members:

WebSocketFrame
~~~~~~~~~~~~~~~

.. autoclass:: WebSocketFrame
    :members:



Errors
-------

.. autoexception:: WebSocketError
    :members:
    :show-inheritance:

WebSocket Frame Errors
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: InvalidWebSocketFrame
    :members:
    :show-inheritance:

.. autoexception:: InvalidWebSocketOpcode
    :members:
    :show-inheritance:

.. autoexception:: InvalidWebSocketCloseCode
    :members:
    :show-inheritance:

WebSocket Control Frame Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: InvalidWebSocketControlFrame
    :members:
    :show-inheritance:

.. autoexception:: FragmentedControlFrame
    :members:
    :show-inheritance:

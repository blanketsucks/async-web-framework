.. currentmodule:: railway.extensions

Extensions API Documentation
================================

Ngrok
-------

.. autoclass:: ngrok.Application
    :members:


.. currentmodule:: railway.extensions.sqlalchemy

SQLAlchemy
------------

.. autoclass:: Engine
    :members:

.. autoclass:: Connection
    :members:

.. autoclass:: Transaction
    :members:

.. autofunction:: create_engine
.. autofunction:: create_connection

Result Cursors
~~~~~~~~~~~~~~~

.. autoclass:: Row
    :members:
    :special-members: __getitem__, __getattr__, __iter__

.. autoclass:: CursorResult
    :members:
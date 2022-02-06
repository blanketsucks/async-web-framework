.. currentmodule:: subway.extensions

Extensions API Documentation
================================


.. currentmodule:: subway.extensions.sqlalchemy

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
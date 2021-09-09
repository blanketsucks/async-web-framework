from setuptools import setup
from Cython.Build import cythonize

extensions = [

]

setup(
    name='railway',
    packages=[
        'railway',
        'railway.client',
        'railway.http',
        'railway.server',
        'railway.rfc6555',
        'railway.websockets',
        'railway-stubs'
    ],
    ext_modules=extensions,
)
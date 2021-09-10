from setuptools import setup
import sys
from Cython.Build import cythonize

requirements = []

if sys.platform != 'win32':
    requirements.append('uvloop')

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
    python_requires='>=3.8.0',
    ext_modules=cythonize('railway/utils.pyx', language_level=3),
)
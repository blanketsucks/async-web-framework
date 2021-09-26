from setuptools import setup
import sys
from Cython.Build import cythonize

with open('requirements.txt', 'r') as file:
    requirements = file.readlines()
    
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
    install_requires=requirements,
)
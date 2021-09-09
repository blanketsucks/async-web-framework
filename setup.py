from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize


setup(
    name='railway',
    packages=[
        'railway',
        'railway.client',
        'railway.http',
        'railway.server',
        'railway.rfc6555',
        'railway.websockets'
    ],
    ext_modules=cythonize('railway/utils.pyx', compiler_directives={'language_level': 3, 'embedsignature': True}),
)
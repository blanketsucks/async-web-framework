from setuptools import find_packages, setup
import sys

with open('requirements.txt', 'r') as file:
    requirements = file.readlines()
    
if sys.platform != 'win32':
    requirements.append('uvloop')

extra_require = {
    'sqlalchemy': [
        'sqlalchemy',
        'sqlalchemy[asyncio]'
    ]
}

packages = find_packages()

setup(
    name='railway',
    packages=packages,
    python_requires='>=3.8.0',
    install_requires=requirements,
    extras_require=extra_require,
)

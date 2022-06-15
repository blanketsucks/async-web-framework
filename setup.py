# from setuptools import find_packages, setup
# import sys

# with open('requirements.txt', 'r') as file:
#     requirements = file.readlines()

# extra_require = {
#     'sqlalchemy': [
#         'sqlalchemy',
#         'sqlalchemy[asyncio]'
#     ],
#     'speed': [
#         'orjson',
#     ]   
# }

# if sys.platform != 'win32':
#     extra_require['speed'].append('uvloop')

# packages = find_packages()

# setup(
#     name='railway',
#     packages=packages,
#     python_requires='>=3.8.0',
#     install_requires=requirements,
#     extras_require=extra_require,
# )

"""
MIT License

Copyright (c) 2021 blanketsucks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import importlib
import sys
from typing import Any, List

from .app import Application
from .utils import get_application_instance

def get(iterable: List[str], index: int) -> str:
    try:
        return iterable[index]
    except IndexError:
        return ''

def import_from_string(string: str):
    if (app := get_application_instance()):
        return app

    if len(string.split(':')) > 2:
        raise ValueError('Invalid input. {file}:{app_variable}')

    file, var = string.split(':')
    module = importlib.import_module(file)

    try:
        app = getattr(module, var)
    except AttributeError:
        raise ValueError('Invalid application variable.')

    if not isinstance(app, Application):
        raise TypeError('Expected Application or App but got {0} instead.'.format(app.__class__.__name__))

    return app

def main():
    app = import_from_string(get(sys.argv, 1))

    try:
        app.run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
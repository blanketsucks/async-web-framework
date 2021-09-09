
import os
import sys
import subprocess
from typing import List

project = os.path.join(os.path.dirname(__file__), 'railway')
path = os.path.dirname(__file__)

def get_pyx_files(path: str):
    pending = []

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.pyx'):
                pending.append(os.path.join(root, file))
            
            elif file.endswith('.c'):
                os.remove(os.path.join(root, file))

    return pending

def build_pyx_files(files: List[str]):
    cython = os.path.dirname(sys.executable) + '/scripts/cython'
    process = subprocess.run([cython] + files)

    if process.returncode != 0:
        raise SystemError('Failed to build pyx files')

def build_extensions(path: str):
    prefix = ['python3.8']
    if sys.platform == 'win32':
        prefix = ['py', '-3.9']

    process = subprocess.run(prefix + [f'{path}/setup.py', 'build_ext', '--inplace'])

    if process.returncode != 0:
        raise SystemError('Failed to build extensions')

def build_docs(path: str):
    docs = os.path.join(path, 'docs')
    process = subprocess.run([f'{docs}/make.bat', 'html'])

    if process.returncode != 0:
        raise SystemError('Failed to build docs')

    return docs + '/_build/html'

def run_docs(path: str):
    prefix = ['python3.8']
    if sys.platform == 'win32':
        prefix = ['py', '-3.9']

    process = subprocess.run(prefix + ['-m', 'http.server'], cwd=path)

    if process.returncode != 0:
        raise SystemError('Failed to run docs')

if __name__ == '__main__':
    # build_extensions(path)

    docs = build_docs(path)
    run_docs(docs)
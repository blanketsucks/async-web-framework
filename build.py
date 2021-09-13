import os
import sys
import subprocess
from typing import List

class Builder:
    def __init__(self) -> None:
        self.base = os.path.dirname(__file__)
        self.project = os.path.join(os.path.dirname(__file__), 'railway')
        self.docs = os.path.join(self.base, 'docs')
        self.build = os.path.join(self.docs, '_build', 'html')

    def get_pyx_files(self):
        pending = []

        for root, _, files in os.walk(self.project):
            for file in files:
                if file.endswith('.pyx'):
                    pending.append(os.path.join(root, file))
                
                elif file.endswith('.c'):
                    os.remove(os.path.join(root, file))

        return pending

    def build_pyx_files(self, files: List[str]):
        cython = os.path.dirname(sys.executable) + '/scripts/cython'
        process = subprocess.run([cython] + files)

        if process.returncode != 0:
            raise SystemError('Failed to build pyx files')

    def build_extensions(self):
        prefix = ['python3.8']
        if sys.platform == 'win32':
            prefix = ['py', '-3.9']

        setup = f'{self.base}/setup.py'
        process = subprocess.run(prefix + [setup, 'build_ext', '--inplace'])

        if process.returncode != 0:
            raise SystemError('Failed to build extensions')

    def build_docs(self):
        make = f'{self.docs}/make.bat'
        process = subprocess.run([make, 'html'])

        if process.returncode != 0:
            raise SystemError('Failed to build docs')

    def run_docs(self):
        prefix = ['python3.8']
        if sys.platform == 'win32':
            prefix = ['py', '-3.9']

        process = subprocess.run(prefix + ['-m', 'http.server'], cwd=self.build)

        if process.returncode != 0:
            raise SystemError('Failed to run docs')
    

if __name__ == '__main__':
    # build_extensions(path)
    builder = Builder()

    builder.build_docs()
    builder.run_docs()
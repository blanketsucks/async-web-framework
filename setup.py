from distutils.core import setup

def read(fn: str):
    with open(fn, 'r') as file:
        return file.read()

def requirements():
    reqs = read('requirements.txt')
    return reqs.splitlines()

def main():
    setup(
        name='atom',
        version = "0.0.1",
        author = "blanketsucks",
        license = "MIT",
        packages=['atom', 'atom.sockets', 'atom.datastructures'],
        long_description=read('README.md'),
        requires=requirements(),
    )

if __name__ == '__main__':
    main()

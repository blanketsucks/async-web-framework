from ..application import Application, Route, Middleware, Listener
from ..error import ExtensionLoadError
from .resource import Resource
from .extension import Extension

import importlib
import typing

class RESTApp(Application):
    def __init__(self, *,
                routes: typing.List[Route]=None,
                listeners: typing.List[Listener]=None,
                middlewares: typing.List[Middleware]=None,
                resources: typing.List[dict]=None,
                extensions: typing.List[str]=None,
                **kwargs) -> None:
        
        self._resources = {}
        self._extensions = {}

        super().__init__(loop=kwargs.get('loop'))
        self._load_from_arguments(resources, extensions, routes=routes, listeners=listeners, middlewares=middlewares)

    @property
    def resources(self):
        return self._resources

    @property
    def extensions(self):
        return self._extensions
    
    def load_extension(self, filepath: str):
        module = importlib.import_module(filepath)

        try:
            load = getattr(module, 'load')
        except AttributeError:
            raise ExtensionLoadError('Missing load function.')

        load(self)
    
    def add_extension(self, extension):
        if not isinstance(extension, Extension):
            raise ValueError('Extension must inherit from Extension')

        ext = extension._unpack()
        self._extensions[ext.__class__.__name__] = ext

        return ext

    def add_resource(self, cls, path: str):
        if not issubclass(cls, Resource):
            raise RuntimeError('Expected Resource but got {0!r} instead.'.format(cls.__name__))
        
        res = cls(self, path)
        res._unpack()

        self._resources[res.__class__.__name__] = res
        return res

    def resource(self, path: str):
        def decorator(cls):
            return self.add_resource(cls, path)
        return decorator

    def _load_from_arguments(self, resources=None, extensions=None, **kwargs):
        routes = kwargs.get('routes')
        listeners = kwargs.get('listeners')
        middlewares = kwargs.get('middlewares')

        if resources:
            for resource in resources:
                for cls, path in resource.items():
                    self.add_resource(cls, path)

        if extensions:
            for extension in extensions:
                self.load_extension(extension)

        super()._load_from_arguments(routes, listeners, middlewares), resources, extensions

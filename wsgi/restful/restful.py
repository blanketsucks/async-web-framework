from ..application import Application
from ..error import ExtensionLoadError
from .endpoint import Endpoint
from .extension import Extension

import importlib
import typing

class App(Application):
    def __init__(self,
                resources: typing.List[dict]=None,
                extensions: typing.List[str]=None,
                **kwargs) -> None:
        
        self._resources = {}
        self._extensions = {}

        super().__init__(loop=kwargs.get('loop'))

        self._load_from_arguments(resources, extensions, **kwargs)

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
            raise ValueError('Extensions must inherit from Extension')

        ext = extension._unpack()
        self._extensions[ext.__extension_name__] = ext

        return ext

    def add_endpoint(self, cls, path: str):
        if not issubclass(cls, Endpoint):
            raise RuntimeError('Expected Endpoint but got {0!r} instead.'.format(cls.__name__))
        
        res = cls(self, path)
        res._unpack()

        self._resources[res.__endpoint_name__] = res
        return res

    def endpoint(self, path: str):
        def decorator(cls):
            return self.add_endpoint(cls, path)
        return decorator

    def _load_from_arguments(self, resources=None, extensions=None, **kwargs):
        routes = kwargs.get('routes')
        listeners = kwargs.get('listeners')
        middlewares = kwargs.get('middlewares')

        if resources:
            for resource in resources:
                for cls, path in resource.items():
                    self.add_endpoint(cls, path)

        if extensions:
            for extension in extensions:
                self.load_extension(extension)

        super()._load_from_arguments(routes, listeners, middlewares)

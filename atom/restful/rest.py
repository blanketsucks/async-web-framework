from ..app import Application
from ..errors import ExtensionLoadError, ExtensionNotFound, EndpointLoadError, EndpointNotFound
from .endpoint import Endpoint
from .extension import Extension

import importlib
import typing

class App(Application):
    def __init__(self,
                endpoints: typing.List[dict]=None,
                extensions: typing.List[str]=None,
                **kwargs) -> None:
        
        self._endpoints: typing.Dict[str, Endpoint] = {}
        self._extensions: typing.Dict[str, Extension] = {}

        super().__init__(loop=kwargs.get('loop'))

        self._load_from_arguments(endpoints, extensions, **kwargs)

    @property
    def endpoints(self):
        return self._endpoints

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
            raise ExtensionLoadError('Expected Extension but got {0!r} instead.'.format(extension.__name__))

        ext = extension._unpack()
        self._extensions[ext.__extension_name__] = ext

        return ext

    def remove_extension(self, name: str):
        if not name in self._extensions:
            raise ExtensionNotFound('{0!r} was not found.'.format(name))

        extension = self._extensions.pop(name)
        extension._pack()

        return extension

    def add_endpoint(self, cls, path: str):
        if not issubclass(cls, Endpoint):
            raise EndpointLoadError('Expected Endpoint but got {0!r} instead.'.format(cls.__name__))
        
        res = cls(self, path)
        res._unpack()

        self._endpoints[res.__endpoint_name__] = res
        return res

    def remove_endpoint(self, name: str):
        if not name in self._endpoints:
            raise EndpointNotFound('{0!r} was not found.'.format(name))

        endpoint = self._endpoints.pop(name)
        endpoint._pack()

        return endpoint

    def endpoint(self, path: str):
        def decorator(cls):
            return self.add_endpoint(cls, path)
        return decorator

    def _load_from_arguments(self, endpoints=None, extensions=None, **kwargs):
        routes = kwargs.get('routes')
        listeners = kwargs.get('listeners')
        middlewares = kwargs.get('middlewares')

        if endpoints:
            for resource in endpoints:
                for cls, path in resource.items():
                    self.add_endpoint(cls, path)

        if extensions:
            for extension in extensions:
                self.load_extension(extension)

        super()._load_from_arguments(routes, listeners, middlewares)

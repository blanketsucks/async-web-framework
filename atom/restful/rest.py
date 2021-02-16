from atom.app import Application
from atom.errors import ExtensionLoadError, ExtensionNotFound, EndpointLoadError, EndpointNotFound
from .endpoint import Endpoint
from .extension import Extension

import importlib
import typing
import inspect

class RESTApplication(Application):
    def __init__(self,
                endpoints: typing.List[typing.Dict[str, Endpoint]]=None,
                extensions: typing.List[str]=None,
                **kwargs) -> None:
        
        self._endpoints: typing.Dict[str, Endpoint] = {}
        self._extensions: typing.Dict[str, Extension] = {}

        super().__init__(**kwargs)
        self._load_others(extensions, endpoints)


    @property
    def endpoints(self):
        return self._endpoints

    @property
    def extensions(self):
        return self._extensions
    
    def register_extension(self, filepath: str) -> typing.List[Extension]:
        try:
            module = importlib.import_module(filepath)
        except Exception as exc:
            raise ExtensionLoadError('Failed to load {0!r}.'.format(filepath)) from exc

        localexts: typing.List[Extension] = []

        for key, value in module.__dict__.items():
            if inspect.isclass(value):
                if issubclass(value, Extension):
                    ext = value(self)
                    ext._unpack()

                    localexts.append(ext)
                    self._extensions[ext.__extension_name__] = ext

        if not localexts:
            raise ExtensionNotFound('No extensions were found for file {0!r}.'.format(filepath))

        return localexts
    
    def remove_extension(self, name: str):
        if not name in self._extensions:
            raise ExtensionNotFound('{0!r} was not found.'.format(name))

        extension = self._extensions.pop(name)
        extension._pack()

        return extension

    def register_endpoint(self, cls, path: str):
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
            return self.register_endpoint(cls, path)
        return decorator

    def _load_others(self, extensions=None, endpoints=None):
        if extensions:
            for ext in extensions:
                self.register_extension(ext)

        if endpoints:
            for endpoint in endpoints:
                for path, cls in endpoint:
                    self.register_endpoint(cls, path)

        return self


import inspect

from .errors import (RouteRegistrationError,
                    ListenerRegistrationError,
                    MiddlewareRegistrationError
                    )

from .utils import VALID_METHODS

__all__ = (
    'ViewMeta',
    'EndpointMeta',
    'ExtensionMeta'
)

class ViewMeta(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        attrs['__url_route__'] = kwargs.get('path', '')

        self = super().__new__(cls, name, bases, attrs)
        view_routes = []

        for base in self.mro():
            for elem, value in base.__dict__.items():
                if inspect.iscoroutinefunction(value):
                    if value.__name__.upper() in VALID_METHODS:
                        view_routes.append(value)

        self.__routes__ = view_routes
        return self

class ExtensionMeta(type):
    def __new__(cls, *args, **kwargs):
        name, bases, attrs = args

        attrs['__extension_route_prefix__'] = kwargs.get('url_prefix', '')
        attrs['__extension_name__'] = kwargs.get('name', name) 
        
        routes = {}
        listeners = {}
        middlewares = []

        self = super().__new__(cls, name, bases, attrs)

        for base in self.mro():
            for element, value in base.__dict__.items():
                is_static = isinstance(value, staticmethod)

                try:
                    route = getattr(value, '__extension_route__')
                    if is_static:
                        raise RouteRegistrationError('Routes must not be static.')

                    routes[route] = value
                except AttributeError:
                    pass

                try:
                    middleware = getattr(value, '__extension_middleware__')
                    if is_static:
                        raise MiddlewareRegistrationError('Middlewares must not be static.')

                    middlewares.append(middleware)
                except AttributeError:
                    pass

                try:
                    listener = getattr(value, '__extension_listener__')
                    if is_static:
                        raise ListenerRegistrationError('Listeners must not be static')

                    listeners[listener] = value
                except AttributeError:
                    pass

        self.__extension_routes__ = routes
        self.__extension_middlewares__ = middlewares
        self.__extension_listeners__ = listeners

        return self

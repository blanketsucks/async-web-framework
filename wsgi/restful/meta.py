
class ResourceMeta(type):
    def __new__(cls, *args, **kwargs):
        name, bases, attrs = args

        routes = {}
        middlewares = []

        self = super().__new__(cls, name, bases, attrs, **kwargs)

        for base in self.mro():
            for element, value in base.__dict__.items():
                is_static = isinstance(value, staticmethod)

                try:
                    route = getattr(value, '__resource_route__')
                    if is_static:
                        raise ValueError('Routes must not be static.')

                    routes[route] = value
                except AttributeError:
                    pass

                try:
                    middleware = getattr(value, '__resource_middleware__')
                    if is_static:
                        raise ValueError('Middlewares must not be static.')

                    middlewares.append(middleware)
                except AttributeError:
                    pass

        self.__resource_routes__ = routes
        self.__resource_middlewares = middlewares

        return self

class ExtensionMeta(type):
    def __new__(cls, *args, **kwargs):
        name, bases, attrs = args

        routes = {}
        listeners = {}
        middlewares = []

        self = super().__new__(cls, name, bases, attrs, **kwargs)

        for base in self.mro():
            for element, value in base.__dict__.items():
                is_static = isinstance(value, staticmethod)

                try:
                    route = getattr(value, '__extension_route__')
                    if is_static:
                        raise ValueError('Routes must not be static.')

                    routes[route] = value
                except AttributeError:
                    pass

                try:
                    middleware = getattr(value, '__extension_middleware__')
                    if is_static:
                        raise ValueError('Middlewares must not be static.')

                    middlewares.append(middleware)
                except AttributeError:
                    pass

                try:
                    listener = getattr(value, '__extension_listener__')
                    if is_static:
                        raise ValueError('Listeners must not be static')

                    listeners[listener] = value
                except AttributeError:
                    pass

        self.__extension_routes__ = routes
        self.__extension_middlewares__ = middlewares
        self.__extension_listeners__ = listeners

        return self

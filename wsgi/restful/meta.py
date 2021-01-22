
class EndpointMeta(type):
    def __new__(cls, *args, **kwargs):
        name, bases, attrs = args
        
        attrs['__endpoint_route_prefix__'] = kwargs.get('url_prefix', '')
        attrs['__endpoint_name__'] = kwargs.get('name', name) 

        routes = {}
        middlewares = []

        self = super().__new__(cls, name, bases, attrs, **kwargs)

        for base in self.mro():
            for element, value in base.__dict__.items():
                is_static = isinstance(value, staticmethod)

                try:
                    route = getattr(value, '__endpoint_route__')
                    if is_static:
                        raise ValueError('Routes must not be static.')

                    routes[route] = value
                except AttributeError:
                    pass

                try:
                    middleware = getattr(value, '__endpoint_middleware__')
                    if is_static:
                        raise ValueError('Middlewares must not be static.')

                    middlewares.append(middleware)
                except AttributeError:
                    pass

        self.__endpoint_routes__ = routes
        self.__endpoint_middlewares = middlewares

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

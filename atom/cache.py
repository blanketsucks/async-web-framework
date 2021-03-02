
from .context import Context
from .request import Request
from .response import Response
from .objects import Route, WebsocketRoute

import asyncio
import typing

__all__ = (
    'Routes',
    'Cache'
)

class Routes(dict):
    def __init__(self, maxsize: int=64, *args, **kwargs):
        self.maxsize = maxsize
        self.currentsize = 0

        super().__init__(*args, **kwargs)

    def update(self, **kwargs):
        self._check_if_full()
        self.currentsize += len(kwargs.keys())

        return super().update(**kwargs)
    
    def __setitem__(self, k: typing.Union[Route, WebsocketRoute], v: Request) -> None:
        self._check_if_full()
    
        if not isinstance(k, (Route, WebsocketRoute)):
            fmt = 'Expected Route or WebsocketRoute but got {0.__class__.__name__} instead'
            raise ValueError(fmt.format(k))

        if not isinstance(v, Request):
            fmt = 'Expected Request but got {0.__class__.__name__} instead'
            raise ValueError(fmt.format(v))
        
        self.currentsize += 1 
        return super().__setitem__(k, v)

    def _check_if_full(self):
        current = self.maxsize
        lenght = len(self.keys())

        if lenght > current:
            to_remove = lenght - current
            keys = []

            for i, k in enumerate(self):
                if i >= to_remove:
                    break

                keys.append(k)

            for key in keys:
                self.currentsize -= 1
                self.pop(key)
            
        return self

    def as_dict(self) -> typing.Dict[typing.Union[Route, WebsocketRoute], Request]:
        return dict(self.items())

    def __repr__(self) -> str:
        return '<Routes maxsize={0.maxsize} currentsize={0.currentsize}>'.format(self)

class Cache(dict):
    def __init__(self, routes_maxsize: int=64, *args, **kwargs):
        self._routes = Routes(routes_maxsize)
    
    @property
    def routes(self):
        return self._routes

    @property
    def last_route(self):
        return self._routes.items()[0]

    def add_route(self, route: typing.Union[Route, WebsocketRoute], request: Request):
        self._routes[route] = request
        return route, request

    def set(self, **kwargs):
        ctx = kwargs.get('context')
        request = kwargs.get('request')
        response = kwargs.get('response')

        if ctx:
            if not isinstance(ctx, Context):
                raise ValueError('Expected Context but got {0.__class__.__name__} instead'.format(ctx))

            self['_context'] = ctx

        if request:
            if not isinstance(request, Request):
                raise ValueError('Expected Request but got {0.__class__.__name__} instead'.format(request))

            self['_request'] = request

        if response:
            if not isinstance(response, Response):
                raise ValueError('Expected Response but got {0.__class__.__name__} instead'.format(response))

            self['_response'] = response

        return self

    @property
    def context(self) -> typing.Optional[Context]:
        return self.get('_context')

    @property
    def request(self) -> typing.Optional[Request]:
        return self.get('_request')

    @property
    def response(self) -> typing.Optional[Response]:
        return self.get('_request')

    def __repr__(self) -> str:
        return '<Cache routes={0.routes} context={0.context} request={0.request} response={0.response}>'.format(self)
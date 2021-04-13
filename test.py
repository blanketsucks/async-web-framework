import asyncio
import functools
import typing
import inspect

class Respect:
    def __init__(self, check_return_annotation: bool=False) -> None:
        self.check_return_annotation = check_return_annotation

    def _get_signature(self, func: typing.Callable):
        signature = inspect.signature(func)
        cls = signature.return_annotation

        if self.check_return_annotation:
            if cls is signature.empty:
                raise ValueError('{0.__name__!r} must have a return annotation'.format(func))

            if cls is None:
                cls = type(None)

            return signature, cls

        return signature

    @staticmethod
    def _check_if_method(func: typing.Callable):
        if hasattr(func, '__self__'):
            return True

        return False

    def _parse_parameter(self, 
                        func: typing.Callable, 
                        parameter: inspect.Parameter) -> typing.Union[bool, type, typing.Sequence[type]]:
        if self._check_if_method(func):
            return None

        if parameter.annotation is parameter.empty:
            if parameter.default is parameter.empty:
                fmt = 'Parameter {0.name} does not have an annotation nor a default value'
                raise ValueError(fmt.format(parameter))

            cls = type(parameter.default)
            return cls

        types = self._get_union_args(parameter.annotation)
        
        if parameter.default is not parameter.empty:
            check = type(parameter.default)
            if check is Ellipsis:
                return types

            if not check in types:
                string = 'Missmatch of types between annotation and default value for parameter {0.name!r}. ' \
                    'Got {1} for annotation and {2.__name__} for the default value'
                error = self._format_string(string, parameter, types, check)
                raise ValueError(error)

            return types
        return types

    def _parse(self, 
                func: typing.Callable,
                parameter: inspect.Parameter, 
                types: typing.Sequence[type], 
                idx: int, 
                args: typing.Tuple, 
                kwargs: typing.Dict):

        if self._check_if_method(func):
            return False

        item = parameter.name
        if type(None) in types:
            try:
                arg = args[idx]
            except IndexError:
                kwargs.setdefault(item, None)

        value = kwargs.get(item, None)
        if not value:
            pass
        else:
            if not isinstance(value, types):
                error = self._format_string('Incorrect argument type for {0}. Expected {1} but got {2.__name__} instead', item, types, value)
                raise ValueError(error)    
        try:
            arg = args[idx]
        except IndexError:
            return False

        if not isinstance(arg, types):
            string = 'Incorrect argument type for {0}. Expected {1} but got {2.__class__.__name__} instead'
            error = self._format_string(string, item, types, arg)

            raise ValueError(error)
        else:
            return False

    @staticmethod
    def _get_union_args(cls: object) -> typing.Union[typing.Tuple, typing.Sequence[type]]:
        args = getattr(cls, '__args__', None)
        if not args:
            return (cls,)

        return args

    @staticmethod
    def _format_string(error: str, param: str, types: typing.Sequence[type], actual: type):
        return error.format(param, ', '.join(cls.__name__ for cls in types), actual)

    def apply(self, *, cls: bool=False):
        is_cls = cls
        def decorator(func):
            if is_cls:
                return self.__apply_to_class()(func)

            items = self._get_signature(func)

            if isinstance(items, tuple):
                signature, return_cls = items
            else:
                signature, return_cls = items, None

            types: typing.List[typing.Tuple[inspect.Parameter, typing.Union[typing.Sequence[type], type]]] = []

            for name, parameter in signature.parameters.items():
                cls = self._parse_parameter(func, parameter)
                types.append((parameter, cls))        

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                for index, (parameter, cls) in enumerate(types):                   
                    if not self._parse(func, parameter, cls, index, args, kwargs):
                        continue

                res = func(*args, **kwargs)

                if self.check_return_annotation:
                    self._check_return_type(res, return_cls)

                return res
            return wrapper
        return decorator

    def _check_return_type(self, res: object, cls: object):
        return_types = self._get_union_args(cls)
        if not isinstance(res, return_types):
            error = 'Expected return type {0} but received {1.__class__.__name__} instead'
            raise ValueError(error.format(', '.join(cls.__name__ for cls in return_types), res))

        return True

    def __add_to_class(self, 
                    cls: object, 
                    name: str, 
                    value: typing.Callable, 
                    *args: typing.Tuple[typing.Any], 
                    **kwargs: typing.Mapping[str, typing.Any]):

        setattr(cls, name, self.apply(*args, **kwargs)(value))

    def __apply_to_class(self, 
                        *args: typing.Tuple[typing.Any], 
                        **kwargs: typing.Mapping[str, typing.Any]):
        def decorator(cls):
            for name, value in cls.__dict__.items():
                if name == '__init__':
                    self.__add_to_class(cls, name, value, *args, **kwargs)

                if name == '__call__':
                    self.__add_to_class(cls, name, value, *args, **kwargs)

                if not name.startswith('__') and not name.endswith('__'):
                    self.__add_to_class(cls, name, value, *args, **kwargs)
            
            return cls
        return decorator

def respect(*args, **kwargs):
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            raise RuntimeError('Use aiorespect instead')
    
        check = kwargs.get('check_return_annotation', False)

        resp = Respect(check)
        return resp.apply(*args, **kwargs)(func)
    return decorator

def aiorespect(*args, **kwargs):
    def decorator(func):
        check = kwargs.get('check_return_annotation', False)    
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):

            resp = Respect(check)
            signature, cls = resp._get_signature(func)

            coro = resp.apply()(func)(*args, **kwargs)
            res = await coro

            if check:
                resp._check_return_type(res, cls)

            return res
        return wrapper
    return decorator


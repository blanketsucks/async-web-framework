
class WebsocketError(Exception):
    pass

class InvalidHandshake(Exception):
    def __init__(self, **kwargs) -> None:
        is_key_error = kwargs.get('key')
        self.message = kwargs.get('message', '')

        if is_key_error:
            self.message = 'Invalid key.'

        super().__init__(self.message)

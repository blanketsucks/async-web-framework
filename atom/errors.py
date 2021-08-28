
class AtomException(Exception):
    """Base inheritance class for errors that occur during the Application's runtime."""
    pass

class ApplicationError(Exception):
    pass

class ConnectionError(AtomException):
    pass

class BadConversion(ApplicationError):
    pass

class InvalidSetting(ApplicationError):
    pass

class RegistrationError(ApplicationError):
    pass

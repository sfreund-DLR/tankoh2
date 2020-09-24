"""Custom exceptions"""

class CustomException(Exception):
    """This class defines and abstract exception class so that customized exceptions
    can be inherited."""

    def __init__(self, value):
        """doc"""
        self.value = value

    def __str__(self):
        """Returning the error message"""
        return repr(self.value)


class Tankoh2Error(CustomException):
    """classdocs"""



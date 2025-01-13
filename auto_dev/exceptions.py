"""Base exceptions for the auto_dev package."""


class OperationError(Exception):
    """Operation error."""


class NotFound(FileNotFoundError):
    """File not found error."""


class NetworkTimeoutError(Exception):
    """Network error."""


class AuthenticationError(Exception):
    """Authentication error."""


class UserInputError(Exception):
    """User input error."""


class ScaffolderError(Exception):
    """Scaffolder error."""


class UnsupportedSolidityVersion(Exception):
    """Exception raised when processing ABIs from unsupported Solidity versions."""

    def __init__(self, message: str = "Unsupported Solidity version", *args, **kwargs):
        """Initialize the exception.

        Args:
            message: Custom error message
        """
        super().__init__(message, *args, **kwargs)

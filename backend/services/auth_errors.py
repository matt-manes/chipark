class AuthenticationError(ValueError):
    """Report an authentication or OAuth configuration failure.

    Notes
    -----
    This exception is used for expected failures in account authentication,
    token handling, and OAuth setup or completion.
    """

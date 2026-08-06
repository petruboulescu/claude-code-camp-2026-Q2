class UnknownToolError(Exception):
    pass


class ApiError(Exception):
    pass


class LoopError(Exception):
    pass


class TurnCancelled(Exception):
    """A cooperative request to stop the current interactive turn."""


class UnsupportedModelError(Exception):
    pass

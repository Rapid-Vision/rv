from . import utils as _utils


def __getattr__(name: str):
    if name == "_ACTIVE_RUN_ID":
        return _utils._ACTIVE_RUN_ID
    raise AttributeError(name)

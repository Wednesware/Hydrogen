from .logging import error
from .config import getconf


def handle(fn: callable) -> any: # type: ignore
    try:
        return fn()
    except Exception as exc:
        error.from_exception(exc).print()
        if getconf("debug", False):
            raise exc
        
def safe(fn: callable) -> callable: # type: ignore
    return lambda *args, **kwargs: handle(lambda: fn(*args, **kwargs))
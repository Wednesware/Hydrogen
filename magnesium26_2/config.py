import os

from .logging import error


class ObjectNotationError(Exception):
    pass

def rf(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path) as file:
        return file.read()

class objectnotation:
    def __init__(self, path: str) -> None:
        self.path: str = path
        if not os.path.exists(path):
            raise ObjectNotationError(f"File not found: {path}")
        
        self.data: any = eval(rf(path), {"rf": rf}) # type: ignore
    def get(self, key: str, else_val: any = None) -> any: # type: ignore
        return self.data.get(key, else_val)
def getconf(key: str, else_value: any = ...) -> any: # type: ignore
    if not os.path.exists("config.pyon"):
        with error("Configuration file not found: config.pyon, creating one for you.") as error_log:
            with open("config.pyon", "w") as file:
                file.write("{}")
            error_log.sublog("'config.pyon' created successfully.")
    if key not in objectnotation("config.pyon").data:
        if else_value is not ...:
            return else_value
        raise ObjectNotationError(f"Configuration key not found: {key}")
    return objectnotation("config.pyon").get(key)
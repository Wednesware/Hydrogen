from __future__ import annotations

import os, sys, importlib, importlib.util, difflib

from .ww.mg26_11.config import ObjectNotation, ObjectNotationError # type: ignore  #COMPAT
from .ww.mg26_11.filepath import FilePath  #COMPAT


class Handler:
    NAME: str = ""
    SAME_NAME_OBJECT: bool = True
    def __init__(self, project: Project):
        self.project: Project = project
    def __getattr__(self, name: str) -> any: # type: ignore
        path_no_ext: str = os.path.join(self.project.path, self.NAME, name)
        path: str = f"{path_no_ext}.py"
        if os.path.isdir(path_no_ext) and not os.path.exists(path):
            return type(self.__class__.__name__ + "_" + name, (self.__class__,), {"NAME": os.path.join(self.NAME, name)})(self.project)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"'{name}' not found in '{self.NAME}'")
        relative_path = os.path.relpath(path_no_ext, self.project.path)
        module_name = ".".join((self.project.name, *relative_path.split(os.sep)))
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load '{module_name}' from '{path}'")
        script = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = script
        spec.loader.exec_module(script)
        modmancer = getattr(self.project, "modmancer", None)
        if modmancer is not None:
            modmancer.patch_module(relative_path, script)
        return getattr(script, name) if self.SAME_NAME_OBJECT else script
    def getFirstMatching(self, query: str) -> any:
        for file in os.listdir(os.path.join(self.project.path, self.NAME)):
            name: str = file.removesuffix(".py")
            if not file.startswith("__") and any([
                query.startswith("*") and query.endswith("*") and query[1:-1] in name,
                query.startswith("*") and name.endswith(query[1:]),
                query.endswith("*") and name.startswith(query[:-1]),
                query == name,
                query == "*",
                "*" in query and name.startswith(query.split("*")[0]) and name.endswith(query.split("*")[-1])
            ]):
                return getattr(self, name)
        raise FileNotFoundError(f"No matching files found in '{self.NAME}' for query '{query}'")
    def getFirst(self) -> any:
        return self.getFirstMatching("*")
    def getRandom(self) -> any:
        import random
        files = [file for file in os.listdir(os.path.join(self.project.path, self.NAME)) if not file.startswith("__")]
        if not files:
            raise FileNotFoundError(f"No files found in '{self.NAME}'")
        random_file = random.choice(files)
        name: str = random_file.removesuffix(".py")
        return getattr(self, name)
    def getRandomMatching(self, query: str) -> any:
        import random
        matching_files = [file for file in os.listdir(os.path.join(self.project.path, self.NAME)) if not file.startswith("__") and any([
            query.startswith("*") and query.endswith("*") and query[1:-1] in file.removesuffix(".py"),
            query.startswith("*") and file.removesuffix(".py").endswith(query[1:]),
            query.endswith("*") and file.removesuffix(".py").startswith(query[:-1]),
            query == file.removesuffix(".py"),
            query == "*",
            "*" in query and file.removesuffix(".py").startswith(query.split("*")[0]) and file.removesuffix(".py").endswith(query.split("*")[-1])
        ])]
        if not matching_files:
            raise FileNotFoundError(f"No matching files found in '{self.NAME}' for query '{query}'")
        random_file = random.choice(matching_files)
        name: str = random_file.removesuffix(".py")
        return getattr(self, name)
    def getClosestMatching(self, query: str) -> any:
        files = [file for file in os.listdir(os.path.join(self.project.path, self.NAME)) if not file.startswith("__")]
        if not files:
            raise FileNotFoundError(f"No files found in '{self.NAME}'")
        closest_match = difflib.get_close_matches(query, [file.removesuffix(".py") for file in files], n=1, cutoff=0.0)
        if not closest_match:
            raise FileNotFoundError(f"No close matches found in '{self.NAME}' for query '{query}'")
        name: str = closest_match[0]
        return getattr(self, name)
    
class ScriptHandler(Handler):
    NAME: str = "scripts"
    SAME_NAME_OBJECT: bool = True
    def __getattr__(self, name: str) -> callable | handler: # type: ignore
        attribute_return: any = super().__getattr__(name) # type: ignore
        if isinstance(attribute_return, Handler):
            return attribute_return
        elif callable(attribute_return):
            return lambda *args, **kwargs: attribute_return(self.project, *args, **kwargs)
        raise TypeError(f"Script '{name}' is not a function")

class ResourceHandler(Handler):
    NAME: str = "resources"
    SAME_NAME_OBJECT: bool = True
    def __getattr__(self, name: str) -> type | Handler:
        attribute_return: any = super().__getattr__(name) # type: ignore
        if isinstance(attribute_return, (type, Handler)):
            return attribute_return
        raise TypeError(f"Resource '{name}' is not a class")

class LibraryHandler(Handler):
    NAME: str = "libraries"
    SAME_NAME_OBJECT: bool = False
    def __getattr__(self, name: str) -> any:
        return super().__getattr__(name) # type: ignore

class ModHandler(Handler):
    NAME: str = "mods"
    SAME_NAME_OBJECT: bool = False
    def __getattr__(self, name: str) -> any:
        return (super().__getattr__(name)) # type: ignore

class Project:
    def __init__(self, cwd: str, name: str):
        self.name: str = name
        self.path: str = os.path.abspath(os.path.join(cwd, "..", self.name))
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Project '{self.name}' not found at path '{self.path}'")
        self.script: ScriptHandler = ScriptHandler(self)
        self.res: ResourceHandler = ResourceHandler(self)
        self.lib: LibraryHandler = LibraryHandler(self)
        self.mod: ModHandler = ModHandler(self)
        self.metadata: dict[str, any] = {}
        self.modmancer: any = None
    def getsetting(self, name: str, else_value: any = "<raiseerror>", scope: str = "prefer args", arg_names: list[str] | None = None) -> any:
        arg_names = [arg_name.format(name=name, n=name[0]) for arg_name in arg_names or ["--{name}", "-{n}"]]
        args_scope_value: str = "<notfound>"
        for i, arg in enumerate(sys.argv[1:], start=1):
            if arg in arg_names:
                try:
                    args_scope_value = sys.argv[i + 1]
                except IndexError:
                    pass
                break
        settings_path: FilePath = FilePath(self.path) / "settings.pyon"
        if not settings_path.exists():
            settings_path.write("{}")
        settings_on: ObjectNotation = ObjectNotation(settings_path)
        settings_scope_value: any = settings_on.get(name, "<notfound>")
        match scope:
            case "only args":
                return_value: any = args_scope_value
            case "only settings":
                return_value: any = settings_scope_value
            case "prefer args":
                return_value: any = settings_scope_value if args_scope_value == "<notfound>" else args_scope_value
            case "prefer settings":
                return_value: any = args_scope_value if settings_scope_value == "<notfound>" else settings_scope_value
            case "return both":
                return {
                    "args": args_scope_value,
                    "settings": settings_scope_value
                }
            case "return none":
                return None
        if return_value == "<notfound>":
            if else_value == "<raiseerror>":
                raise ValueError(f"setting '{name}' was not provided.")
            return else_value
        return return_value
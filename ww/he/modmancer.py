from __future__ import annotations

import builtins, os, tarfile, tempfile, fnmatch, subprocess, threading, importlib.util

from .mg26_11.config import ObjectNotation # type: ignore  #COMPAT
from .mg26_11.filepath import FilePath  #COMPAT


RESERVED_FILES: set[str] = {"__mod__.py", "modmancer.pyon", "MODINFO.md", "LICENSE.md", ".nitrodep"}
ROLES: tuple[str, ...] = ("before", "after", "replace", "syncwith", "delete")


class ModmancerError(Exception):
    pass


def _empty_entry() -> dict[str, list[callable]]:
    return {role: [] for role in ROLES}


def _empty_node() -> dict[str, any]:
    return {"funcs": {}, "classes": {}, "class_hooks": {}}


def _make_decorators(stack: list[dict[str, any]]) -> dict[str, callable]:
    def _make_decorator(role: str) -> callable:
        def decorator(target: callable) -> callable:
            node: dict[str, any] = stack[-1]
            if isinstance(target, type):
                if role == "syncwith":
                    raise ModmancerError("'@syncwith' cannot be used on a class")
                node["class_hooks"].setdefault(target.__name__, _empty_entry())[role].append(target)
            else:
                node["funcs"].setdefault(target.__name__, _empty_entry())[role].append(target)
            return target
        return decorator
    return {role: _make_decorator(role) for role in ROLES}


def _make_build_class(stack: list[dict[str, any]]) -> callable:
    # intercepts `class` statements so nested classes register onto the current scope of `stack`
    def build_class(func: callable, name: str, *bases, **kwargs) -> type:
        node: dict[str, any] = _empty_node()
        stack.append(node)
        try:
            cls: type = builtins.__build_class__(func, name, *bases, **kwargs)
        finally:
            stack.pop()
        stack[-1]["classes"][name] = node
        return cls
    return build_class

class Modmancer:
    def __init__(self, project) -> None:
        self.project = project
        self.mods_path: str = os.path.join(self.project.path, "mods")
        # patches[relative_path] -> node tree: {"funcs": {name: {role: [callable]}}, "classes": {name: node}}
        self.patches: dict[str, dict[str, any]] = {}
        self.loaded_mods: list[dict] = []

    def start(self) -> None:
        self.project.modmancer = self
        if not os.path.isdir(self.mods_path):
            return
        for mod_filename in sorted(os.listdir(self.mods_path)):
            if not mod_filename.endswith(".modm"):
                continue
            self._load_mod(os.path.join(self.mods_path, mod_filename))

    def patch_module(self, relative_path: str, module: any) -> None:
        """Applies any registered mod patches to functions/classes defined in `module`, loaded from `relative_path`."""
        key: str = relative_path.replace(os.sep, "/")
        node = self.patches.get(key)
        if not node:
            return
        self._apply_node(module, node)

    def _load_mod(self, mod_path: str) -> None:
        mod_stem: str = FilePath(mod_path).stem
        extract_dir: str = tempfile.mkdtemp(prefix=f"_modmancer_{mod_stem}_")
        with tarfile.open(mod_path, "r:gz") as archive:
            archive.extractall(extract_dir)
        root: str = self._find_mod_root(extract_dir)
        info: dict | None = self._read_modinfo(root)
        if info is not None and not self._applies_to_project(info):
            return
        self._run_nitrodep(root)
        self._run_mod_entrypoint(root)
        self._collect_overlays(root)
        self.loaded_mods.append({"path": mod_path, "root": root, "info": info})

    def _find_mod_root(self, extract_dir: str) -> str:
        for dirpath, _, filenames in os.walk(extract_dir):
            if "modmancer.pyon" in filenames:
                return dirpath
        return extract_dir

    def _read_modinfo(self, root: str) -> dict | None:
        pyon_path: str = os.path.join(root, "modmancer.pyon")
        if not os.path.isfile(pyon_path):
            return None
        return ObjectNotation(pyon_path).data

    def _applies_to_project(self, info: dict) -> bool:
        pattern: str = info.get("for", "*")
        return fnmatch.fnmatch(self.project.name, pattern)

    def _run_nitrodep(self, root: str) -> None:
        if not os.path.isfile(os.path.join(root, ".nitrodep")):
            return
        try:
            subprocess.run(["n2", "getdep", root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass # nitrogen (n2) is not installed, skip dependency resolution

    def _run_mod_entrypoint(self, root: str) -> None:
        entry_path: str = os.path.join(root, "__mod__.py")
        if not os.path.isfile(entry_path):
            return
        spec = importlib.util.spec_from_file_location(f"_modmancer_entry_{os.path.basename(root)}", entry_path)
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        module.project = self.project # type: ignore
        spec.loader.exec_module(module)

    def _collect_overlays(self, root: str) -> None:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for filename in filenames:
                if filename in RESERVED_FILES or not filename.endswith(".py"):
                    continue
                file_path: str = os.path.join(dirpath, filename)
                relative: str = os.path.relpath(file_path, root)
                key: str = relative[:-len(".py")].replace(os.sep, "/")
                self._register_overlay(key, file_path)

    def _register_overlay(self, key: str, file_path: str) -> None:
        root: dict[str, any] = _empty_node()
        stack: list[dict[str, any]] = [root]
        source: str = FilePath(file_path).read()
        code = compile(source, file_path, "exec")
        exec_globals: dict[str, any] = {
            "__name__": f"_modmancer_overlay_{key.replace('/', '_')}",
            "__builtins__": {**vars(builtins), "__build_class__": _make_build_class(stack)},
            **_make_decorators(stack),
        }
        exec(code, exec_globals)
        self._merge_node(self.patches.setdefault(key, _empty_node()), root)

    def _merge_node(self, dest: dict[str, any], src: dict[str, any]) -> None:
        for name, entry in src["funcs"].items():
            target: dict[str, list[callable]] = dest["funcs"].setdefault(name, _empty_entry())
            for role, funcs in entry.items():
                target[role].extend(funcs)
        for name, entry in src["class_hooks"].items():
            target = dest["class_hooks"].setdefault(name, _empty_entry())
            for role, funcs in entry.items():
                target[role].extend(funcs)
        for name, child in src["classes"].items():
            self._merge_node(dest["classes"].setdefault(name, _empty_node()), child)

    def _apply_node(self, obj: any, node: dict[str, any]) -> None:
        for name, entry in node["funcs"].items():
            if not hasattr(obj, name) or not callable(getattr(obj, name)):
                continue
            setattr(obj, name, self._build_wrapper(getattr(obj, name), entry))
        for name, child in node["classes"].items():
            if not hasattr(obj, name):
                continue
            self._apply_node(getattr(obj, name), child)
            hooks = node["class_hooks"].get(name)
            if hooks and hasattr(obj, name):
                setattr(obj, name, self._build_wrapper(getattr(obj, name), hooks))

    def _build_wrapper(self, original: callable, entry: dict[str, list[callable]]) -> callable:
        if entry["delete"]:
            def deleted(*args, **kwargs) -> any:
                raise ModmancerError(f"'{original.__name__}' has been deleted by a mod")
            deleted.__name__ = original.__name__
            return deleted
        target: callable = entry["replace"][-1] if entry["replace"] else original
        befores, afters, syncs = entry["before"], entry["after"], entry["syncwith"]
        def wrapper(*args, **kwargs) -> any:
            threads: list[threading.Thread] = [threading.Thread(target=sync, args=args, kwargs=kwargs) for sync in syncs]
            for thread in threads:
                thread.start()
            for before_func in befores:
                before_func(*args, **kwargs)
            result: any = target(*args, **kwargs)
            for after_func in afters:
                after_func(*args, **kwargs)
            for thread in threads:
                thread.join()
            return result
        wrapper.__name__ = original.__name__
        return wrapper
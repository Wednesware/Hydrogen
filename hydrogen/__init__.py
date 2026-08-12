import sys, zipfile, shutil, os, urllib.error, subprocess, traceback, tarfile, asyncio, re, tempfile, platform
from dataclasses import dataclass, field
from urllib.request import urlretrieve

from .ww.mg26_11.config import getconf
from .ww.mg26_11.filepath import FilePath


SOURCEGEN_VERSION: str = "26.5" # SHOULD NOT BE CHANGED

NAME: str = "Hydrogen" # TODO
DESCRIPTION: str = "Official and community-made distribution installer." # TODO
VERSION: str = "26.1" # TODO
COMMAND: str = f"h2" # TODO

CLI_RESET: str = "\033[0m"
CLI_BOLD: str = "\033[1m"
CLI_DIM: str = "\033[90m"
CLI_INFO: str = "\033[94m"
CLI_SUCCESS: str = "\033[92m"
CLI_WARNING: str = "\033[93m"
CLI_ERROR: str = "\033[91m"

EXTENSIONS_DIR: str = os.path.join(os.path.dirname(__file__), "extensions")
TRUSTED_EXTENSIONS_FILE: str = os.path.join(os.path.dirname(__file__), ".TRUSTED_EXTENSIONS")
LEN_PATH: str = os.path.join(os.path.dirname(__file__), "ww", "len")
HYDROSTAGED_FILE: str = ".hydrostaged"
# "internal" installs live inside the hydrogen package itself (not the cwd), so commands like
INTERNAL_WW_DIR: str = os.path.join(os.path.dirname(__file__), "ww")
INTERNAL_TEMP_DIR: str = os.path.join(INTERNAL_WW_DIR, "temp")
CONFIG_PATH: FilePath = FilePath(__file__) / ".." / "config.pyon"
DSTBS_DIR: str = {
    "linux": "/var/lib/dstbs",
    "windows": "C:\\ProgramData\\Distrobase\\dstbs",
    "darwin": "/Library/Application Support/Distrobase/dstbs"
}[platform.system().lower()]

running_installs: dict[tuple[str, str], asyncio.Task] = {}

def getAddress(address: str) -> dict:
    address = address.strip()
    if not address:
        raise ValueError("Address is empty.")
    home_registry: str = getconf("registry", "wednesware.org", config_path=CONFIG_PATH)
    addr_type: str = "registry" if "@" in address else ("local" if "#" in address else "")
    if not addr_type:
        addr_type = "local" if home_registry.startswith("#") else "registry"
    parts: list[str] = address.split("@", maxsplit=1) if addr_type == "registry" else address.split("#", maxsplit=1)
    if len(parts) == 1:
        parts.append(home_registry.removeprefix("#"))
    author: str = parts[0].split(".")[0] if "." in parts[0] else ""
    if not author:
        author = parts[1].split(".")[0].split(":")[0] if addr_type == "registry" else "localhost"
    distro: str = parts[0].split(".", maxsplit=1)[-1]
    version: str = parts[1].split("=", maxsplit=1)[1] if "=" in parts[1] else "latest"
    parts[1] = parts[1].split("=", maxsplit=1)[0]
    if addr_type == "local" and not parts[1]:
        parts[1] = DSTBS_DIR
    return {
        "address": address,
        "author": author,
        "distro": distro,
        "registry": parts[1],
        "version": version,
        "type": addr_type
    }

@dataclass(slots=True)
class InstallResult:
    status: str = "info"
    lines: list[str] = field(default_factory=list)
    exit_code: int = 0
    success: bool = False
    message: str = ""

def cli(text: str, color: str = "", bold: bool = False) -> str:
    prefix: str = f"{CLI_BOLD if bold else ''}{color}"
    return f"{prefix}{text}{CLI_RESET if prefix else ''}"

def printStatus(label: str, message: str, tone: str = "info") -> None:
    palette: dict[str, str] = {
        "info": CLI_INFO,
        "success": CLI_SUCCESS,
        "warning": CLI_WARNING,
        "error": CLI_ERROR,
        "muted": CLI_DIM
    }
    color: str = palette.get(tone, "")
    print(f"{cli(f'[{label}]', color, bold=True)} {message}")

def printSection(title: str) -> None:
    print(cli(title, CLI_BOLD))

def printCommand(signature: str, description: str) -> None:
    print(f"  {cli(signature, CLI_INFO)} {cli('-', CLI_DIM)} {description}")

def printHelp() -> None:
    print(cli(f"{NAME} v{VERSION}", CLI_INFO, bold=True))
    print(cli(DESCRIPTION, CLI_DIM))
    print()
    printSection("Usage")
    print(f"  {COMMAND} <command> [args]")
    print()
    printSection("General")
    printCommand("get <address>", "Download a distribution from a Wednesware address.")
    printCommand("view <address>", "View information about a distribution.")
    printCommand("getlib <project> <address>", "Download a distribution into '<project>/libraries/ww'.")
    printCommand("rm <address>", "Delete one distribution or all installed distributions.")
    printCommand("getdep [path]", "Install missing dependencies from a .hydrodep file, including nested ones.")
    printCommand("forcegetdep [path]", "Install all dependencies, regardless of whether they are already installed from a .hydrodep file, including nested ones, forcing reinstallation of all dependencies.")
    printCommand("updlibs <project>", "Reinstall all distributions in '<project>/libraries' from their exact installed addresses.")
    printCommand("registry <registry>", "Set your home registry which will be used in operations when a registry is not specified.")
    print()
    printSection("Compatibility")
    printCommand("compat <mode> <address|directory> [custom-phrase]", "Rewrite Wednesware imports in a directory to match the specified compatibility mode.")
    printCommand("compat abs <address|directory>", "Use 'abs' for packages found in '.'. ")
    printCommand("compat rel <address|directory>", "Use 'rel' for packages found in '<project>'.")
    printCommand("compat rel-up1 <address|directory>", "Use 'rel-up1' for packages found in '<project>/../'.")
    printCommand("compat rel-up2 <address|directory>", "Use 'rel-up2' for packages found in '<project>/../../'.")
    printCommand("compat rel-up3 <address|directory>", "Use 'rel-up3' for packages found in '<project>/../../../'.")
    printCommand("compat abs-ww <address|directory>", "Use 'abs-ww' for packages found in './ww'. Default compat mode.")
    printCommand("compat rel-ww <address|directory>", "Use 'rel-ww' for packages found in '<project>/ww' with relative imports.")
    printCommand("compat rel-libs-ww <address|directory>", "Use 'rel-libs-ww' for Helium projects or packages found in '<project>/libraries/ww' with relative imports.")
    printCommand("compat custom <address|directory> <custom-phrase>", "Use 'custom' to specify a custom phrase for the import prefix.")
    print()
    printSection("Stage")
    printCommand("stage get <address>", "Stage a dependency install into ./ww.")
    printCommand("stage getlib <project> <address>", "Stage a library install into ./<project>/libraries/ww.")
    printCommand("stage adddep <address>", "Stage adding one dependency line to ./.hydrodep.")
    printCommand("stage rmdep <address>", "Stage removing one dependency line from ./.hydrodep.")
    printCommand("stage getdep [target]", "Stage running getdep at ./<target>.")
    printCommand("stage forcegetdep [target]", "Stage running forcegetdep at ./<target>.")
    printCommand("stage updlibs [target]", "Stage running updlibs at ./<target>.")
    printCommand("stage rm <address>", "Stage dependency removal from ./ww.")
    printCommand("stage rmlib <project> <address>", "Stage library removal from ./<project>/libraries/ww.")
    printCommand("stage compat <mode> <address|directory> [custom-phrase]", "Stage compatibility rewrite for Wednesware imports in a directory.")
    printCommand("stage cmd <command>", "Stage a shell command to run during stage execute/commit.")
    printCommand("stage getinternal <address>", "Stage a dependency install into hydrogen/ww.")
    printCommand("stage rminternal <address>", "Stage dependency removal from hydrogen/ww.")
    printCommand("stage getdepinternal [target]", "Stage running getdep against hydrogen/ww at ./<target>.")
    printCommand("stage cancel [subcommand|last] [args]", "Cancel one staged line, the last line, or the full stage.")
    printCommand("stage execute", "Execute staged actions in exact order. Slower but guarantees order of operations.")
    printCommand("stage commit", "Execute staged installs/removals in batched mode. Faster but does not guarantee order of operations.")
    print()
    print()
    printSection("Documentation")
    printCommand("readme [extension]", "Show the README for Hydrogen or an installed extension.")
    printCommand("license [extension]", "Show the license for Hydrogen or an installed extension.")
    printCommand("help", "Show this help message.")
    print()
    printSection("Extensions")
    printCommand("list-ext", "List installed extensions and their local paths.")
    printCommand("trust-ext <extension>", "Trust an extension so it can run without confirmation.")
    printCommand("untrust-ext <extension>", "Remove trust for an extension.")
    printCommand("install-ext <extension>", "Install an extension from LEN.")
    printCommand("uninstall-ext <extension>", "Remove an installed extension.")
    printCommand("list-len", "List available extensions in LEN.")
    printCommand("load-len", "Clone the LEN repository locally.")
    printCommand("unload-len", "Remove the local LEN checkout.")

def printInstalledExtensions() -> None:
    printSection("Installed extensions")
    sent: bool = False
    for ext_filename in [item for item in os.listdir(EXTENSIONS_DIR) if item.endswith(".n2x")]:
        print(f"  {cli(ext_filename, CLI_INFO)} {cli('->', CLI_DIM)} {os.path.join(EXTENSIONS_DIR, ext_filename)}")
        sent = True
    if not sent:
        printStatus("empty", "No extensions were detected.", "warning")


def printLenExtensions() -> None:
    printSection("Available extensions")
    printed: bool = False
    for ext_filename in [item for item in os.listdir(LEN_PATH) if item.endswith(".n2x")]:
        print(f"  {cli(ext_filename, CLI_INFO)} {cli('->', CLI_DIM)} https://github.com/Wednesware/LEN/blob/main/{ext_filename}")
        printed = True
    if not printed:
        printStatus("empty", "No extensions were detected in the LEN repository.", "warning")


def printExtensionCommands() -> None:
    printSection("Custom commands")
    printed: bool = False
    for ext_path in [item for item in os.listdir(EXTENSIONS_DIR) if item.endswith(".n2x")]:
        print(f"  {cli(ext_path.removesuffix('.n2x'), CLI_INFO)} {cli('-', CLI_DIM)} Provided by '{ext_path}' at '{os.path.join(EXTENSIONS_DIR, ext_path)}'")
        printed = True
    if not printed:
        print(f"  {cli('(none installed)', CLI_DIM)}")

def addressDirname(address: str, root: str = "ww") -> str:
    return os.path.join(root, address)

def dependencyFilePath(path: str) -> str:
    if path.endswith(".hydrodep"):
        return path
    return os.path.join(path, ".hydrodep")

def printInstallResult(result: InstallResult, color: bool = True) -> None:
    labels: dict[str, str] = {
        "info": "skip",
        "success": "done",
        "error": "fail",
    }
    palette: dict[str, str] = {
        "info": CLI_INFO,
        "success": CLI_SUCCESS,
        "error": CLI_ERROR,
    }
    prefix: str = palette.get(result.status, "") if color else ""
    label: str = labels.get(result.status, "info")
    lines: list[str] = list(result.lines) if result.lines else ([result.message] if result.message else [])
    for line in lines:
        if prefix:
            print(f"{cli(f'[{label}]', prefix, bold=True)} {line}")
        else:
            print(f"[{label}] {line}")

def stageFilePath() -> str:
    return os.path.join(".", HYDROSTAGED_FILE)

def readStageLines() -> list[str]:
    path: str = stageFilePath()
    if not os.path.exists(path):
        return []
    with open(path) as file:
        return [line.rstrip("\n") for line in file if line.strip()]

def writeStageLines(lines: list[str]) -> None:
    path: str = stageFilePath()
    if not lines:
        if os.path.exists(path):
            os.remove(path)
        return

    with open(path, "w") as file:
        file.write("\n".join(lines) + "\n")

def appendStageLine(line: str) -> None:
    lines: list[str] = readStageLines()
    lines.append(line)
    writeStageLines(lines)

def findHydrodepFiles(root_path: str) -> list[str]:
    if root_path.endswith(".hydrodep") and os.path.isfile(root_path):
        return [root_path]
    found: list[str] = []
    for current_root, _, files in os.walk(root_path):
        if ".hydrodep" in files:
            found.append(os.path.join(current_root, ".hydrodep"))
    return sorted(found)

def readHydrodepEntries(dep_path: str) -> list[str]:
    if not os.path.isfile(dep_path):
        return []

    entries: list[str] = []
    with open(dep_path) as file:
        for raw_line in file:
            line: str = raw_line.strip()
            if not line:
                continue
            address: str = line.split()[0].strip().lower()
            if address:
                entries.append(address)
    return entries


def writeHydrodepEntries(dep_path: str, entries: list[str]) -> None:
    parent: str = os.path.dirname(dep_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(dep_path, "w") as file:
        if entries:
            file.write("\n".join(entries) + "\n")


def addHydrodepDependency(path: str, address: str) -> bool:
    dep_path: str = dependencyFilePath(path)
    normalized_address: str = address
    entries: list[str] = readHydrodepEntries(dep_path)
    if normalized_address in entries:
        return False
    entries.append(normalized_address)
    writeHydrodepEntries(dep_path, entries)
    return True


def removeHydrodepDependency(path: str, address: str) -> bool:
    dep_path: str = dependencyFilePath(path)
    if not os.path.isfile(dep_path):
        return False

    normalized_address: str = address
    entries: list[str] = readHydrodepEntries(dep_path)
    filtered: list[str] = [entry for entry in entries if entry != normalized_address]
    if len(filtered) == len(entries):
        return False
    writeHydrodepEntries(dep_path, filtered)
    return True


def stageTagForCommand(command: str) -> str | None:
    return {
        "get": "GET",
        "getlib": "GETLIB",
        "adddep": "ADDDEP",
        "rmdep": "RMDEP",
        "getdep": "GETDEP",
        "forcegetdep": "FORCEGETDEP",
        "updlibs": "UPDLIBS",
        "compat": "COMPAT",
        "rm": "RM",
        "rmlib": "RMLIB",
        "cmd": "RUNCMD",
    }.get(command.lower())


COMPAT_TAG: str = "#COMPAT"
COMPAT_BUILTIN_PREFIXES: dict[str, str] = {
    "abs-ww": "ww",
    "abs": "",
    "rel": "",
    "rel-up1": ".",
    "rel-up2": "..",
    "rel-up3": "...",
    "rel-ww": ".ww",
    "rel-libs-ww": ".libraries.ww",
}
COMPAT_TAG: str = "#COMPAT"
# Each compat mode is pure data: a prefix plus a join strategy, so adding a new mode never
# requires touching the transform logic below - just add an entry here.
#   "dot"      -> collapse the boundary between a trailing "." on the prefix and the sub-path's
#                 leading "." into a single "." (namespace-style prefixes, e.g. "ww.", ".ww.")
#   "raw"      -> concatenate prefix and sub-path verbatim, no collapsing (every "." is
#                 meaningful, e.g. "up N levels" relative prefixes)
#   "strip"    -> drop the sub-path's own leading "." entirely (plain absolute imports)
#   "identity" -> the sub-path is already in canonical form; only the empty-path fallback is used
COMPAT_MODES: dict[str, tuple[str, str]] = {
    "abs-ww": ("ww.", "dot"),
    "abs": ("", "strip"),
    "rel": (".", "identity"),
    "rel-up1": ("..", "raw"),
    "rel-up2": ("...", "raw"),
    "rel-up3": ("....", "raw"),
    "rel-ww": (".ww.", "dot"),
    "rel-libs-ww": (".libraries.ww.", "dot"),
}
_COMPAT_LINE_RE = re.compile(r'^(\s*)from\s+(?:\.?(?:libraries\.)?)ww(\.[^\s]*|)(\s+import\s+.*)$')
_COMPAT_TAGGED_LINE_RE = re.compile(r'^(\s*)from\s+(\S+)(\s+import\s+.*)$')

def compatNewPath(mode: str, custom_phrase: str, rest: str) -> str | None:
    if mode == "custom":
        return custom_phrase + rest
    if mode == "abs":
        # absolute import with no leading dot, so drop the leading dot ww left on the sub-path
        sub: str = rest[1:] if rest.startswith(".") else rest
        return sub or None
    if mode in ("rel", "rel-up1", "rel-up2", "rel-up3"):
        # rest already carries its own leading dot (or is empty), so the prefix here holds only
        # the *extra* up-level dots; pad with a bare "." when rest is empty to keep dot counts consistent
        prefix: str = COMPAT_BUILTIN_PREFIXES[mode]
        return prefix + rest if rest else prefix + "."
    return COMPAT_BUILTIN_PREFIXES[mode] + rest

def compatRestFromTaggedPath(path: str, custom_phrase: str) -> str:
    # recover the canonical (dot-prefixed) sub-path after "ww" from a path already rewritten by any builtin/custom mode
    for prefix in (".libraries.ww", ".ww", "ww"):
        if path.startswith(prefix):
            return path[len(prefix):]
    if custom_phrase and path.startswith(custom_phrase):
        return path[len(custom_phrase):]
    stripped: str = path.lstrip(".")
    if path and stripped != path:
        # path was purely dots (rel/rel-upN result), so re-normalize to a single leading dot (or none)
        # instead of keeping every up-level dot, which would compound on repeated transforms
        return "." + stripped if stripped else ""
    if path in ("", "."):
        return ""
    return path if path.startswith(".") else "." + path

def compatTransformLine(line: str, mode: str, custom_phrase: str) -> str | None:
    ending: str = "\n" if line.endswith("\n") else ""
    body: str = line[:-1] if ending else line
    stripped: str = body.strip()
    is_tagged: bool = stripped.endswith(COMPAT_TAG)
    if not (stripped.startswith("from ww") or is_tagged):
        return None
    working: str = body
    if working.rstrip().endswith(COMPAT_TAG):
        tag_index: int = working.rstrip().rfind(COMPAT_TAG)
        working = working[:tag_index].rstrip()

    if is_tagged:
        tagged_match: re.Match | None = _COMPAT_TAGGED_LINE_RE.match(working)
        if tagged_match is None:
            return None
        leading_ws, path, import_clause = tagged_match.group(1), tagged_match.group(2), tagged_match.group(3)
        rest: str = compatRestFromTaggedPath(path, custom_phrase)
    else:
        match: re.Match | None = _COMPAT_LINE_RE.match(working)
        if match is None:
            return None
        leading_ws, rest, import_clause = match.group(1), match.group(2), match.group(3)

    new_path: str | None = compatNewPath(mode, custom_phrase, rest)
    if new_path is None:
        return None
    new_body: str = f"from {leading_ws}{new_path}{import_clause}  {COMPAT_TAG}"
    if new_body == body:
        return None
    return new_body + ending

def iterPythonFiles(root: str):
    if os.path.isfile(root):
        if root.endswith(".py"):
            yield root
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)

def applyCompat(directory: str, mode: str, custom_phrase: str) -> tuple[int, int]:
    files_changed: int = 0
    lines_changed: int = 0
    for path in iterPythonFiles(directory):
        with open(path) as file:
            lines: list[str] = file.readlines()
        changed: bool = False
        for i, line in enumerate(lines):
            new_line: str | None = compatTransformLine(line, mode, custom_phrase)
            if new_line is not None:
                lines[i] = new_line
                changed = True
                lines_changed += 1
        if changed:
            with open(path, "w") as file:
                file.writelines(lines)
            files_changed += 1
    return files_changed, lines_changed


def removeAddressVersions(install_root: str, address: str) -> int:
    if not os.path.isdir(install_root):
        return 0

    deleted: int = 0
    normalized_address: str = address
    for path in os.listdir(install_root):
        full_path: str = os.path.join(install_root, path)
        if not os.path.isdir(full_path):
            continue

        path_lower: str = path.lower()
        should_delete: bool = path_lower == normalized_address or path_lower.startswith(f"{normalized_address}")
        if should_delete:
            shutil.rmtree(full_path)
            deleted += 1

    return deleted


def parseInstalledAddressDir(dirname: str) -> tuple[str, str] | None:
    directory_name: str = dirname.lower()
    if not directory_name:
        return None
    return directory_name, "latest"


@dataclass(slots=True)
class StageAction:
    action: str
    args: list[str]
    raw: str


def parseStageLine(line: str) -> StageAction | None:
    if line.startswith("RUNCMD|"):
        return StageAction("RUNCMD", [line[len("RUNCMD|"):]], line)
    parts: list[str] = line.split("|")
    if not parts:
        return None
    action: str = parts[0]
    args: list[str] = parts[1:]
    arity: dict[str, int] = {
        "ADDDEP": 2,
        "ADDLIB": 3,
        "ADDNDEP": 2,
        "RMNDEP": 2,
        "GETDEP": 1,
        "FORCEGETDEP": 1,
        "UPDLIBS": 1,
        "RMDEP": 2,
        "RMLIB": 3,
        "COMPAT": 3,
    }
    if action not in arity:
        return None
    if len(args) != arity[action]:
        return None
    return StageAction(action, args, line)


def runStagedCommand(command: str) -> None:
    printStatus("cmd", command, "info")
    result: subprocess.CompletedProcess = subprocess.run(command, shell=True, cwd=os.getcwd())
    if result.returncode != 0:
        printStatus("fail", f"Command failed with exit code {result.returncode}: {command}", "error")
        raise SystemExit(result.returncode)


def _install_address_to_root(address: str, install_root: str, reinstall: bool = True, work_dir: str = ".") -> InstallResult:
    return installAddressToRoot(address, install_root, reinstall, work_dir)


def queueInstallToRoot(address: str, install_root: str = "ww", reinstall: bool = True, work_dir: str = ".") -> asyncio.Task:
    resolved_address: str = address
    key: tuple[str, str] = (resolved_address.lower(), os.path.realpath(install_root))
    if key in running_installs:
        printStatus("wait", f"Already queued {resolved_address.lower()} -> {install_root}", "muted")
        return running_installs[key]

    printStatus("queue", f"{resolved_address.lower()} -> {install_root}", "info")
    task: asyncio.Task = asyncio.create_task(asyncio.to_thread(_install_address_to_root, resolved_address, install_root, reinstall, work_dir))
    running_installs[key] = task

    def cleanup(completed_task: asyncio.Task, install_key: tuple[str, str] = key) -> None:
        if running_installs.get(install_key) is completed_task:
            running_installs.pop(install_key, None)

    task.add_done_callback(cleanup)
    return task


async def executeStageOrdered(actions: list[StageAction]) -> None:
    for action in actions:
        if action.action == "ADDDEP":
            address, version = action.args
            result: InstallResult = await queueInstallToRoot(address, version, "ww", True)
            printInstallResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        elif action.action == "ADDLIB":
            project, address, version = action.args
            install_root: str = os.path.join(project, "libraries", "ww")
            result = await queueInstallToRoot(address, version, install_root, True)
            printInstallResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        elif action.action == "ADDNDEP":
            address, version = action.args
            if addHydrodepDependency(".", address, version):
                printStatus("done", f"Added dependency '{address} {version}' to ./.hydrodep.", "success")
            else:
                printStatus("info", f"Dependency '{address} {version}' is already in ./.hydrodep.", "muted")
        elif action.action == "RMNDEP":
            address, version = action.args
            if removeHydrodepDependency(".", address, version):
                printStatus("done", f"Removed dependency '{address} {version}' from ./.hydrodep.", "success")
            else:
                printStatus("miss", f"Dependency '{address} {version}' was not found in ./.hydrodep.", "warning")
        elif action.action == "GETDEP":
            target = action.args[0]
            await getDepEverywhere(target)
        elif action.action == "FORCEGETDEP":
            target = action.args[0]
            await getDepEverywhere(target, force=True)
        elif action.action == "UPDLIBS":
            project = action.args[0]
            await reinstallProjectLibraries(project)
        elif action.action == "RMDEP":
            address, version = action.args
            deleted: int = removeAddressVersions("ww", address, version)
            printStatus("done", f"Removed {deleted} version{'s' if deleted != 1 else ''} of '{address}' ({version}) from ./ww.", "success")
        elif action.action == "RMLIB":
            project, address, version = action.args
            install_root = os.path.join(project, "libraries", "ww")
            deleted = removeAddressVersions(install_root, address, version)
            printStatus("done", f"Removed {deleted} version{'s' if deleted != 1 else ''} of '{address}' ({version}) from ./{project}/libraries/ww.", "success")
        elif action.action == "RUNCMD":
            runStagedCommand(action.args[0])
        elif action.action == "COMPAT":
            mode, target, custom_phrase = action.args
            files_changed, lines_changed = applyCompat(target, mode, custom_phrase)
            printStatus("done", f"Compatibility rewrite completed: {files_changed} file{'s' if files_changed != 1 else ''} changed with {lines_changed} line{'s' if lines_changed != 1 else ''} modified.", "success")


async def commitStageBatched(actions: list[StageAction]) -> None:
    add_dep: list[tuple[str, str]] = []
    add_lib: list[tuple[str, str, str]] = []
    rm_dep: list[tuple[str, str]] = []
    rm_lib: list[tuple[str, str, str]] = []

    for action in actions:
        if action.action == "ADDDEP":
            add_dep.append((action.args[0], action.args[1]))
        elif action.action == "ADDLIB":
            add_lib.append((action.args[0], action.args[1], action.args[2]))
        elif action.action == "RMDEP":
            rm_dep.append((action.args[0], action.args[1]))
        elif action.action == "RMLIB":
            rm_lib.append((action.args[0], action.args[1], action.args[2]))

    add_dep_address: set[tuple[str, str]] = {(address, version) for address, version in add_dep}
    rm_dep_address: set[tuple[str, str]] = {(address, version) for address, version in rm_dep}
    dep_conflicts: set[tuple[str, str]] = add_dep_address & rm_dep_address
    if dep_conflicts:
        text: str = ", ".join(f"{address} {version}" for address, version in sorted(dep_conflicts))
        printStatus("fail", f"Cannot commit: adddep and rmdep conflict for {text}", "error")
        raise SystemExit(1)

    add_lib_address: set[tuple[str, str, str]] = {(project, address, version) for project, address, version in add_lib}
    rm_lib_address: set[tuple[str, str, str]] = {(project, address, version) for project, address, version in rm_lib}
    lib_conflicts: set[tuple[str, str, str]] = add_lib_address & rm_lib_address
    if lib_conflicts:
        text = ", ".join(f"{project}:{address} {version}" for project, address, version in sorted(lib_conflicts))
        printStatus("fail", f"Cannot commit: addlib and rmlib conflict in same stage for {text}", "error")
        raise SystemExit(1)

    command_failures: int = 0
    for action in actions:
        if action.action == "RUNCMD":
            try:
                runStagedCommand(action.args[0])
            except SystemExit as err:
                command_failures = int(err.code) if isinstance(err.code, int) else 1
                break
        elif action.action == "ADDNDEP":
            address, version = action.args
            if addHydrodepDependency(".", address, version):
                printStatus("done", f"Added dependency '{address} {version}' to ./.hydrodep.", "success")
            else:
                printStatus("info", f"Dependency '{address} {version}' is already in ./.hydrodep.", "muted")
        elif action.action == "RMNDEP":
            address, version = action.args
            if removeHydrodepDependency(".", address, version):
                printStatus("done", f"Removed dependency '{address} {version}' from ./.hydrodep.", "success")
            else:
                printStatus("miss", f"Dependency '{address} {version}' was not found in ./.hydrodep.", "warning")
        elif action.action == "GETDEP":
            target = action.args[0]
            await getDepEverywhere(target)
        elif action.action == "FORCEGETDEP":
            target = action.args[0]
            await getDepEverywhere(target, force=True)
        elif action.action == "UPDLIBS":
            project = action.args[0]
            await reinstallProjectLibraries(project)
    if command_failures:
        raise SystemExit(command_failures)

    install_tasks: list[asyncio.Task] = []
    for address, version in add_dep:
        install_tasks.append(queueInstallToRoot(address, version, "ww", True))
    for project, address, version in add_lib:
        install_tasks.append(queueInstallToRoot(address, version, os.path.join(project, "libraries", "ww"), True))

    if install_tasks:
        install_results: list[InstallResult] = await asyncio.gather(*install_tasks)
        install_failures: int = 0
        for result in install_results:
            printInstallResult(result)
            install_failures += int(bool(result.exit_code))
        if install_failures:
            printStatus("fail", f"Commit install finished with {install_failures} failure{'s' if install_failures != 1 else ''}.", "error")
            raise SystemExit(1)

    for address, version in rm_dep:
        deleted: int = removeAddressVersions("ww", address, version)
        printStatus("done", f"Removed {deleted} version{'s' if deleted != 1 else ''} of '{address}' ({version}) from ./ww.", "success")
    for project, address, version in rm_lib:
        install_root: str = os.path.join(project, "libraries", "ww")
        deleted = removeAddressVersions(install_root, address, version)
        printStatus("done", f"Removed {deleted} version{'s' if deleted != 1 else ''} of '{address}' ({version}) from ./{project}/libraries/ww.", "success")


async def runStaged(mode: str) -> None:
    lines: list[str] = readStageLines()
    if not lines:
        printStatus("info", "Nothing staged.", "muted")
        return

    actions: list[StageAction] = []
    for line in lines:
        parsed: StageAction | None = parseStageLine(line)
        if parsed is None:
            printStatus("fail", f"Invalid stage line: {line}", "error")
            raise SystemExit(1)
        actions.append(parsed)

    if mode == "execute":
        await executeStageOrdered(actions)
    else:
        await commitStageBatched(actions)

    writeStageLines([])
    printStatus("done", f"Stage completed in {mode} mode.", "success")

async def handleStageCommand(args: list[str]) -> None:
    if not args:
        printStatus("help", f"Usage: {COMMAND} stage <get|getlib|adddep|rmdep|getdep|forcegetdep|updlibs|rm|rmlib|compat|cmd|getinternal|rminternal|getdepinternal|cancel|execute|commit> [...]", "warning")
        sys.exit(1)

    subcommand: str = args[0].lower()

    if subcommand == "get":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage get <address> [version]", "warning")
            sys.exit(1)
        address: str = args[1]
        version: str = args[2] if len(args) > 2 else "latest"
        appendStageLine(f"ADDDEP|{address}|{version}")
        printStatus("stage", f"Staged get {address} {version}", "success")
        return

    if subcommand == "getlib":
        if len(args) < 3:
            printStatus("help", f"Usage: {COMMAND} stage getlib <project> <address> [version]", "warning")
            sys.exit(1)
        project: str = args[1]
        address = args[2]
        version = args[3] if len(args) > 3 else "latest"
        appendStageLine(f"ADDLIB|{project}|{address}|{version}")
        printStatus("stage", f"Staged getlib {project} {address} {version}", "success")
        return

    if subcommand == "adddep":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage adddep <address> [version]", "warning")
            sys.exit(1)
        address = args[1]
        version = args[2] if len(args) > 2 else "latest"
        appendStageLine(f"ADDNDEP|{address}|{version}")
        printStatus("stage", f"Staged adddep {address} {version}", "success")
        return

    if subcommand == "rmdep":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage rmdep <address> [version]", "warning")
            sys.exit(1)
        address = args[1]
        version = args[2] if len(args) > 2 else "latest"
        appendStageLine(f"RMNDEP|{address}|{version}")
        printStatus("stage", f"Staged rmdep {address} {version}", "success")
        return

    if subcommand == "getdep":
        if len(args) > 2:
            printStatus("help", f"Usage: {COMMAND} stage getdep [target]", "warning")
            sys.exit(1)
        target: str = args[1] if len(args) > 1 else "."
        appendStageLine(f"GETDEP|{target}")
        printStatus("stage", f"Staged getdep {target}", "success")
        return

    if subcommand == "forcegetdep":
        if len(args) > 2:
            printStatus("help", f"Usage: {COMMAND} stage forcegetdep [target]", "warning")
            sys.exit(1)
        target = args[1] if len(args) > 1 else "."
        appendStageLine(f"FORCEGETDEP|{target}")
        printStatus("stage", f"Staged forcegetdep {target}", "success")
        return

    if subcommand == "updlibs":
        if len(args) > 2:
            printStatus("help", f"Usage: {COMMAND} stage updlibs [target]", "warning")
            sys.exit(1)
        target = args[1] if len(args) > 1 else "."
        appendStageLine(f"UPDLIBS|{target}")
        printStatus("stage", f"Staged updlibs {target}", "success")
        return

    if subcommand == "rm":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage rm <address> [version]", "warning")
            sys.exit(1)
        address = args[1]
        version = args[2] if len(args) > 2 else "latest"
        appendStageLine(f"RMDEP|{address}|{version}")
        printStatus("stage", f"Staged rm {address} {version}", "success")
        return

    if subcommand == "rmlib":
        if len(args) < 3:
            printStatus("help", f"Usage: {COMMAND} stage rmlib <project> <address> [version]", "warning")
            sys.exit(1)
        project: str = args[1]
        address = args[2]
        version = args[3] if len(args) > 3 else "latest"
        appendStageLine(f"RMLIB|{project}|{address}|{version}")
        printStatus("stage", f"Staged rmlib {project} {address} {version}", "success")
        return

    if subcommand == "getinternal":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage getinternal <address> [version]", "warning")
            sys.exit(1)
        address = args[1]
        version = args[2] if len(args) > 2 else "latest"
        appendStageLine(f"GETINTERNAL|{address}|{version}")
        printStatus("stage", f"Staged getinternal {address} {version}", "success")
        return

    if subcommand == "rminternal":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage rminternal <address> [version]", "warning")
            sys.exit(1)
        address = args[1]
        version = args[2] if len(args) > 2 else "latest"
        appendStageLine(f"RMINTERNAL|{address}|{version}")
        printStatus("stage", f"Staged rminternal {address} {version}", "success")
        return

    if subcommand == "getdepinternal":
        if len(args) > 2:
            printStatus("help", f"Usage: {COMMAND} stage getdepinternal [target]", "warning")
            sys.exit(1)
        target = args[1] if len(args) > 1 else "."
        appendStageLine(f"GETDEPINTERNAL|{target}")
        printStatus("stage", f"Staged getdepinternal {target}", "success")
        return

    if subcommand == "compat":
        if len(args) < 3:
            printStatus("help", f"Usage: {COMMAND} stage compat <mode> <address|directory> [custom-phrase]", "warning")
            sys.exit(1)
        mode: str = args[1]
        target: str = args[2]
        if mode not in COMPAT_MODES and mode != "custom":
            printStatus("help", f"Usage: {COMMAND} stage compat <mode(abs|rel|rel-up1|rel-up2|rel-up3|abs-ww|rel-ww|rel-libs-ww|custom)> <address|directory> [custom-phrase]", "warning")
            sys.exit(1)
        custom_phrase: str = ""
        if mode == "custom":
            if len(args) < 4:
                printStatus("help", f"Usage: {COMMAND} stage compat custom <address|directory> <custom-phrase>", "warning")
                sys.exit(1)
            custom_phrase = args[3]
        appendStageLine(f"COMPAT|{mode}|{target}|{custom_phrase}")
        printStatus("stage", f"Staged compat {mode} {target}", "success")
        return

    if subcommand == "cmd":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage cmd <command>", "warning")
            sys.exit(1)
        command: str = " ".join(args[1:])
        appendStageLine(f"RUNCMD|{command}")
        printStatus("stage", f"Staged cmd: {command}", "success")
        return

    if subcommand == "cancel":
        lines: list[str] = readStageLines()
        if not lines:
            printStatus("info", "Nothing staged.", "muted")
            sys.exit(0)

        if len(args) == 1:
            writeStageLines([])
            printStatus("done", "Cleared entire stage.", "success")
            sys.exit(0)

        if args[1].lower() == "last":
            removed_line: str = lines.pop()
            writeStageLines(lines)
            printStatus("done", f"Canceled last staged line: {removed_line}", "success")
            sys.exit(0)

        command_name: str = args[1].lower()
        tag: str | None = stageTagForCommand(command_name)
        if tag is None:
            printStatus("help", f"Usage: {COMMAND} stage cancel [get|getlib|adddep|rmdep|getdep|forcegetdep|updlibs|rm|rmlib|compat|cmd|getinternal|rminternal|getdepinternal|last] [args]", "warning")
            sys.exit(1)

        target_line: str | None = None
        if tag == "GET":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel get <address> [version]", "warning")
                sys.exit(1)
            address: str = args[2]
            version: str = args[3] if len(args) > 3 else "latest"
            target_line = f"ADDDEP|{address}|{version}"
        elif tag == "GETLIB":
            if len(args) < 4:
                printStatus("help", f"Usage: {COMMAND} stage cancel getlib <project> <address> [version]", "warning")
                sys.exit(1)
            project = args[2]
            address = args[3]
            version = args[4] if len(args) > 4 else "latest"
            target_line = f"ADDLIB|{project}|{address}|{version}"
        elif tag == "ADDDEP":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel adddep <address> [version]", "warning")
                sys.exit(1)
            address = args[2]
            version = args[3] if len(args) > 3 else "latest"
            target_line = f"ADDNDEP|{address}|{version}"
        elif tag == "RMDEP":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel rmdep <address> [version]", "warning")
                sys.exit(1)
            address = args[2]
            version = args[3] if len(args) > 3 else "latest"
            target_line = f"RMNDEP|{address}|{version}"
        elif tag == "GETDEP":
            if len(args) > 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel getdep [target]", "warning")
                sys.exit(1)
            target: str = args[2] if len(args) > 2 else "."
            target_line = f"GETDEP|{target}"
        elif tag == "FORCEGETDEP":
            if len(args) > 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel forcegetdep [target]", "warning")
                sys.exit(1)
            target = args[2] if len(args) > 2 else "."
            target_line = f"FORCEGETDEP|{target}"
        elif tag == "UPDLIBS":
            if len(args) > 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel updlibs [target]", "warning")
                sys.exit(1)
            target = args[2] if len(args) > 2 else "."
            target_line = f"UPDLIBS|{target}"
        elif tag == "RM":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel rm <address> [version]", "warning")
                sys.exit(1)
            address = args[2]
            version = args[3] if len(args) > 3 else "latest"
            target_line = f"RMDEP|{address}|{version}"
        elif tag == "RMLIB":
            if len(args) < 4:
                printStatus("help", f"Usage: {COMMAND} stage cancel rmlib <project> <address> [version]", "warning")
                sys.exit(1)
            project = args[2]
            address = args[3]
            version = args[4] if len(args) > 4 else "latest"
            target_line = f"RMLIB|{project}|{address}|{version}"
        elif tag == "COMPAT":
            if len(args) < 5:
                printStatus("help", f"Usage: {COMMAND} stage cancel compat <mode> <target> <custom_phrase>", "warning")
                sys.exit(1)
            mode = args[2]
            target = args[3]
            custom_phrase = args[4]
            target_line = f"COMPAT|{mode}|{target}|{custom_phrase}"
        elif tag == "RUNCMD":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel cmd <command>", "warning")
                sys.exit(1)
            command = " ".join(args[2:])
            target_line = f"RUNCMD|{command}"
        elif tag == "GETINTERNAL":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel getinternal <address> [version]", "warning")
                sys.exit(1)
            address = args[2]
            version = args[3] if len(args) > 3 else "latest"
            target_line = f"GETINTERNAL|{address}|{version}"
        elif tag == "RMINTERNAL":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel rminternal <address> [version]", "warning")
                sys.exit(1)
            address = args[2]
            version = args[3] if len(args) > 3 else "latest"
            target_line = f"RMINTERNAL|{address}|{version}"
        elif tag == "GETDEPINTERNAL":
            if len(args) > 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel getdepinternal [target]", "warning")
                sys.exit(1)
            target = args[2] if len(args) > 2 else "."
            target_line = f"GETDEPINTERNAL|{target}"

        if target_line is None:
            printStatus("fail", "Could not build a stage target for cancellation.", "error")
            sys.exit(1)

        try:
            lines.remove(target_line)
        except ValueError:
            printStatus("miss", f"No matching staged line found: {target_line}", "warning")
            sys.exit(1)

        writeStageLines(lines)
        printStatus("done", f"Canceled: {target_line}", "success")
        return

    if subcommand in {"execute", "commit"}:
        await runStaged(subcommand)
        return

    printStatus("help", f"Unknown stage subcommand: {subcommand}", "warning")
    printStatus("help", f"Usage: {COMMAND} stage <get|getlib|adddep|rmdep|getdep|forcegetdep|updlibs|rm|rmlib|compat|cmd|getinternal|rminternal|getdepinternal|cancel|execute|commit> [...]", "warning")
    sys.exit(1)
    
async def reinstallProjectLibraries(project: str) -> None:
    install_root: str = os.path.join(project, "libraries", "ww")
    if not os.path.isdir(install_root):
        printStatus("miss", f"No library directory found at '{install_root}'.", "warning")
        raise SystemExit(1)

    entries: list[str] = [item for item in os.listdir(install_root) if os.path.isdir(os.path.join(install_root, item))]
    if not entries:
        printStatus("info", f"No installed libraries found in '{install_root}'.", "muted")
        return

    tasks: list[asyncio.Task] = []
    ignored: int = 0
    for entry in entries:
        parsed: tuple[str, str] | None = parseInstalledAddressDir(entry)
        if parsed is None:
            ignored += 1
            printStatus("skip", f"Could not parse installed library directory '{entry}'.", "warning")
            continue
        pub, rel = parsed
        tasks.append(queueInstallToRoot(pub, rel, install_root, True))

    if not tasks:
        printStatus("miss", "No reinstallable libraries were found.", "warning")
        if ignored:
            printStatus("info", f"Ignored {ignored} unrecognized directory(ies).", "muted")
        return

    results: list[InstallResult] = await asyncio.gather(*tasks)
    failures: int = 0
    for result in results:
        printInstallResult(result)
        failures += int(bool(result.exit_code))
    if failures:
        printStatus("fail", f"Library reinstall finished with {failures} failure{'s' if failures != 1 else ''}.", "error")
        raise SystemExit(1)

    printStatus("done", f"Reinstalled {len(results)} librar{'y' if len(results) == 1 else 'ies'} from {install_root}.", "success")

def installAddress(address: str, reinstall: bool = True) -> InstallResult:
    return installAddressToRoot(address, "ww", reinstall)


def installAddressToRoot(address: str, install_root: str = "ww", reinstall: bool = True, work_dir: str = ".") -> InstallResult:
    install_root = os.path.abspath(install_root)
    work_dir = os.path.abspath(work_dir)

    os.makedirs(install_root, exist_ok=True)
    os.makedirs(work_dir, exist_ok=True)

    if os.path.exists(install_root) and os.listdir(install_root):
        if not reinstall:
            return InstallResult(status="error", success=False, message=f"Address is already installed at {install_root}", lines=[f"Address is already installed at {install_root}"], exit_code=1)

        for name in os.listdir(install_root):
            path = os.path.join(install_root, name)
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    temp_dir = tempfile.mkdtemp(prefix="hydrogen-install-", dir=work_dir)
    try:
        archive = os.path.join(temp_dir, f"{address}.zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.txt", f"Placeholder install for {address}\n")
        extracted = os.path.join(temp_dir, "extracted")
        os.makedirs(extracted, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extracted)
        entries = os.listdir(extracted)
        source_root = os.path.join(extracted, entries[0]) if len(entries) == 1 and os.path.isdir(os.path.join(extracted, entries[0])) else extracted
        for name in os.listdir(source_root):
            source = os.path.join(source_root, name)
            destination = os.path.join(install_root, name)
            shutil.move(source, destination)

        return InstallResult(status="success", success=True, lines=[f"Installed {address} to {install_root}"], message=f"Installed {address} to {install_root}", exit_code=0)

    except Exception as exc:
        if os.path.exists(install_root):
            for name in os.listdir(install_root):
                path = os.path.join(install_root, name)
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        return InstallResult(status="error", success=False, lines=[f"Failed to install {address}: {exc}"], message=f"Failed to install {address}: {exc}", exit_code=1)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def queueInstall(address: str, reinstall: bool = True, install_root: str = "ww", work_dir: str = ".") -> asyncio.Task:
    return queueInstallToRoot(address, install_root, reinstall, work_dir)

async def installAsync(address: str, reinstall: bool = True, color: bool = True, emit: bool = True, fatal: bool = True, install_root: str = "ww", work_dir: str = ".") -> InstallResult:
    result: InstallResult = await asyncio.to_thread(queueInstallToRoot, address, install_root, reinstall, work_dir)
    if emit:
        printInstallResult(result, color)
    if fatal and result.exit_code:
        raise SystemExit(result.exit_code)
    return result


async def getdepRecursive(path: str, color: bool = True, log: bool = True, visited: set[str] | None = None, installed: set[str] | None = None, force: bool = False, install_root: str = "ww", work_dir: str = ".") -> None:
    dep_path: str = dependencyFilePath(path)
    if visited is None:
        visited = set()
    if installed is None:
        installed = set()
    resolved_path: str = os.path.realpath(dep_path)
    if resolved_path in visited:
        return
    visited.add(resolved_path)

    if not os.path.isfile(dep_path):
        printStatus("miss", f"No dependency file found at '{dep_path}'", "warning")
        return
    with open(dep_path) as file:
        content: str = file.read()
    deps: list[str] = [
        line.split()[0].strip()
        for line in content.split("\n")
        if line.strip() and not line.strip().startswith("//")
    ]
    if not deps:
        if log:
            printStatus("done", "No dependencies needed.", "success")
        return
    if log:
        printStatus("deps", f"Loaded {len(deps)} dependenc{'y' if len(deps) == 1 else 'ies'} from {dep_path}", "info")
    pending_deps: list[str] = []
    scripts_allowed: bool = "allow" if "--allow" in sys.argv else ("skip" if "--skip" in sys.argv else "deny")
    print_tip: bool = False
    for address in deps:
        dep_key: str = address
        if dep_key in installed:
            continue
        if address.lower().startswith("script:"):
            if scripts_allowed == "allow":
                printStatus("script", f"Executing script dependency: {address}", "info")
                script_path: str = address[len("script:"):]
                if not os.path.isfile(script_path):
                    printStatus("fail", f"Script file '{script_path}' not found.", "error")
                    raise SystemExit(1)
                try:
                    with open(script_path) as script_file:
                        script_content: str = script_file.read()
                    exec(script_content, {"__name__": "__main__"})
                except Exception:
                    printStatus("fail", f"Error executing script '{script_path}':\n{traceback.format_exc()}", "error")
                    raise SystemExit(1)
            elif scripts_allowed == "skip":
                printStatus("skip", f"Skipping script dependency: {address}", "muted")
            else:
                printStatus("deny", f"Script dependency '{address}' is not allowed. Use '--allow' to allow or '--skip' to skip.", "error")
                raise SystemExit(1)
            continue
        installed.add(dep_key)
        pending_deps.append(dep_key)
    if print_tip:
        printStatus("deny", "To allow scripts, re-run with '--allow'. To skip scripts, re-run with '--skip'.", "info")
    tasks: list[asyncio.Task] = [queueInstall(address, (force), install_root, work_dir) for address in pending_deps]
    results: list[InstallResult] = await asyncio.gather(*tasks)
    for result in results:
        printInstallResult(result, color)

    failures: int = sum(1 for result in results if result.exit_code)
    if failures:
        if log:
            printStatus("fail", f"Dependency install finished with {failures} failure{'s' if failures != 1 else ''}.", "error")
        raise SystemExit(1)

    for address in deps:
        installed_dep_path: str = dependencyFilePath(addressDirname(address, install_root))
        await getdepRecursive(installed_dep_path, color=color, log=False, visited=visited, installed=installed, install_root=install_root, work_dir=work_dir)
    if log:
        printStatus("done", "All dependencies are ready.", "success")


async def getDep(path: str, color: bool = True, log: bool = True, force: bool = False, install_root: str = "ww", work_dir: str = ".") -> None:
    await getdepRecursive(path, color=color, log=log, force=force, install_root=install_root, work_dir=work_dir)


async def getDepEverywhere(path: str, color: bool = True, force: bool = False, install_root: str = "ww", work_dir: str = ".") -> None:
    dep_files: list[str] = findHydrodepFiles(path)
    if not dep_files:
        printStatus("miss", f"No .hydrodep files found under '{path}'.", "warning")
        return

    printStatus("deps", f"Found {len(dep_files)} .hydrodep file{'s' if len(dep_files) != 1 else ''} under '{path}'.", "info")
    visited: set[str] = set()
    installed: set[str] = set()
    for dep_file in dep_files:
        await getdepRecursive(dep_file, color=color, log=True, visited=visited, installed=installed, force=force, install_root=install_root, work_dir=work_dir)


async def installSubdependencies(address: str, color: bool = True, install_root: str = "ww", work_dir: str = ".") -> None:
    resolved_address: str = address
    dep_path: str = dependencyFilePath(addressDirname(resolved_address, install_root))
    printStatus("deps", f"Checking sub-dependencies for {resolved_address}", "info")
    if not os.path.isfile(dep_path):
        printStatus("info", "No sub-dependencies declared.", "muted")
        return
    await getDep(dep_path, color=color, log=True, install_root=install_root, work_dir=work_dir)
        
def trust(ext_filename: str, ext_dir_path: str) -> None:
    ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
    if not os.path.exists(ext_path):
        print(f"\033[91mExtension '{ext_filename}' not found and cannot be trusted.")
        return
    with open(TRUSTED_EXTENSIONS_FILE) as file:
        content: str = file.read()
    if ext_filename not in content:
        try:
            if input(f"\033[38;5;208m/!\\ WARNING: You are running this extension for the first time.\n    Make sure to review the contents of\n      \033[0;1;3m{ext_dir_path}\033[0;38;5;208m\n    before running.\n    Trust extension and run command? (y/N) \033[0m").strip().lower() in ["y", "yes", "yeah", "true", "t"]:
                with open(TRUSTED_EXTENSIONS_FILE, "a") as file:
                    file.write(f"{ext_filename}\n")
            else:
                raise KeyboardInterrupt
        except (KeyboardInterrupt, EOFError):
            print("\n\033[91m    Extension not trusted. Aborting.\033[0m")
            sys.exit(0)
            
def loadLen() -> None:
    try:
        if os.path.exists(LEN_PATH):
            unloadLen()
        printStatus("sync", "Loading LEN from GitHub...", "info")
        proc = subprocess.Popen(
            [
                "git",
                "clone",
                "--progress",
                "https://github.com/Wednesware/LEN.git",
                LEN_PATH,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in proc.stdout:
            print(cli(f"  {line.rstrip()}", CLI_DIM))
        if proc.returncode != 0 and proc.returncode is not None:
            raise subprocess.CalledProcessError(proc.returncode, proc.args)
        proc.wait()
        printStatus("done", "LEN loaded successfully.", "success")
    except subprocess.CalledProcessError:
        printStatus("fail", "Could not load LEN from GitHub. Are you sure you have an internet connection?", "error")
        sys.exit(1)
        
def unloadLen() -> None:
    if os.path.exists(LEN_PATH):
        shutil.rmtree(LEN_PATH)
        printStatus("done", "LEN unloaded.", "success")
    else:
        printStatus("info", "LEN is not loaded.", "muted")

async def build(format: str, source_path: str = ".", output_path: str = "build.%") -> None:
    printStatus("build", "Preparing build...", "info")
    try:
        output_path = output_path.replace("%", {
            "zip": "zip",
            "targz": "tar.gz",
            "n2x": "n2x",
            "modm": "modm"
        }[format])
    except KeyError:
        printStatus("fail", f"Unknown build format '{format}'.", "error")
        return
    if not os.path.isdir(source_path):
        printStatus("fail", f"Source path '{source_path}' does not exist or is not a directory.", "error")
        return
    source_abs: str = os.path.abspath(source_path)
    output_abs: str = os.path.abspath(output_path)
    output_dir: str = os.path.dirname(output_abs)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    def should_skip(path: str) -> bool:
        return os.path.abspath(path) == output_abs

    match format:
        case "zip":
            printStatus("build", f"Building project into {output_path}...", "info")
            with zipfile.ZipFile(output_abs, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_abs):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if should_skip(file_path):
                            continue
                        arcname = os.path.relpath(file_path, source_abs)
                        printStatus("pack", f"Packing {arcname}", "info")
                        zipf.write(file_path, arcname)
            printStatus("done", f"Build complete in {output_path}", "success")
        case "targz":
            printStatus("build", f"Building project into {output_path}...", "info")
            with tarfile.open(output_abs, "w:gz") as tar:
                for root, dirs, files in os.walk(source_abs):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if should_skip(file_path):
                            continue
                        arcname = os.path.relpath(file_path, source_abs)
                        printStatus("pack", f"Packing {arcname}", "info")
                        tar.add(file_path, arcname=arcname)
            printStatus("done", f"Build complete in {output_path}", "success")
        case "n2x":
            printStatus("build", f"Building project into {output_path}...", "info")
            required_files = ["ext.py", "README.md", "LICENSE.md", ".hydrodep"]
            with tarfile.open(output_abs, "w:gz") as tar:
                for file in required_files:
                    file_path = os.path.join(source_abs, file)
                    printStatus("pack", f"Packing {file}", "info")
                    if not os.path.isfile(file_path):
                        printStatus("fail", f"Required file for build not found: '{file}'", "error")
                        return
                    tar.add(file_path, arcname=file)
            printStatus("done", f"Build complete in {output_path}", "success")
        case "modm":
            printStatus("build", f"Building project into {output_path}...", "info")
            with tarfile.open(output_abs, "w:gz") as tar:
                for root, dirs, files in os.walk(source_abs):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if should_skip(file_path):
                            continue
                        arcname = os.path.relpath(file_path, source_abs)
                        printStatus("pack", f"Packing {arcname}", "info")
                        tar.add(file_path, arcname=arcname)
            printStatus("done", f"Build complete in {output_path}", "success")
        case _:
            printStatus("fail", f"Unknown build format '{format}'.", "error")

async def main() -> None:
    if len(sys.argv) == 1:
        print(cli(f"{NAME} v{VERSION}", CLI_INFO, bold=True))
        print(cli(DESCRIPTION, CLI_DIM))
        print()
        print(f"Usage: {COMMAND} <command> [args]")
        print(f"Run {cli(f'{COMMAND} help', CLI_INFO)} for a full command list.")
        sys.exit(0)
    if not os.path.exists(EXTENSIONS_DIR):
        os.makedirs(EXTENSIONS_DIR)
    if not os.path.exists(TRUSTED_EXTENSIONS_FILE):
        with open(TRUSTED_EXTENSIONS_FILE, "w") as file:
            file.write("")
    
    match sys.argv[1]:
        case "get":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} get <address> [version]", "warning")
                sys.exit(1)
            address: str = sys.argv[2]
            version: str = sys.argv[3] if len(sys.argv) > 3 else "latest"
            result: InstallResult = await installAsync(address, version)
            if not result.exit_code:
                await installSubdependencies(address, version)
        case "getlib":
            if len(sys.argv) < 4:
                printStatus("help", f"Usage: {COMMAND} getlib <project> <address> [version]", "warning")
                sys.exit(1)
            project: str = sys.argv[2]
            address = sys.argv[3]
            version = sys.argv[4] if len(sys.argv) > 4 else "latest"
            install_root: str = os.path.join(project, "libraries", "ww")
            result = await queueInstallToRoot(address, version, install_root, True)
            printInstallResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        case "rm":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} rm <address> [version]", "warning")
                sys.exit(1)
            pub: str = sys.argv[2]
            printStatus("rm", f"Deleting {pub}", "info")
            if pub.strip() == "all":
                if os.path.exists("ww"):
                    shutil.rmtree("ww")
                else:
                    printStatus("info", "No address installed.", "muted")
            else:
                if len(sys.argv) > 3:
                    rel: str = sys.argv[3]
                    deleted: int = removeAddressVersions("ww", pub, rel)
                    if deleted:
                        printStatus("done", "Operation complete.", "success")
                    else:
                        printStatus("miss", f"Version '{rel}' of address '{pub.capitalize()}' is not installed here. Are you sure you spelled it right?", "warning")
                else:
                    deleted: int = removeAddressVersions("ww", pub)
                    if deleted:
                        printStatus("done", "Operation complete.", "success")
                    else:
                        printStatus("miss", f"Address '{pub.capitalize()}' is not installed here. Are you sure you spelled it right?", "warning")
        case "getdep":
            path: str = sys.argv[2] if len(sys.argv) > 2 else "."
            await getDepEverywhere(path)
        case "forcegetdep":
            path: str = sys.argv[2] if len(sys.argv) > 2 else "."
            await getDepEverywhere(path, force=True)
        case "updlibs":
            if len(sys.argv) < 3:
                printStatus("help", f"Usage: {COMMAND} updlibs <project>", "warning")
                sys.exit(1)
            await reinstallProjectLibraries(sys.argv[2])
        case "compat":
            if len(sys.argv) < 4:
                printStatus("help", f"Usage: {COMMAND} compat <address|directory> <mode(abs|rel|rel-up1|rel-up2|rel-up3|abs-ww|rel-ww|rel-libs-ww|custom)> [custom-phrase]", "warning")
                sys.exit(1)
            compat_target: str = sys.argv[3]
            compat_mode: str = sys.argv[2]
            if compat_mode not in COMPAT_BUILTIN_PREFIXES and compat_mode != "custom":
                printStatus("help", f"Usage: {COMMAND} compat <address|directory> <mode(abs|rel|rel-up1|rel-up2|rel-up3|abs-ww|rel-ww|rel-libs-ww|custom)> [custom-phrase]", "warning")
                sys.exit(1)
            compat_custom_phrase: str = ""
            if compat_mode == "custom":
                if len(sys.argv) < 5:
                    printStatus("help", f"Usage: {COMMAND} compat <address|directory> custom <custom-phrase>", "warning")
                    sys.exit(1)
                compat_custom_phrase = sys.argv[4]

            compat_dirs: list[str]
            if "/" in compat_target:
                compat_dirs = [compat_target]
            else:
                compat_dirs = []
                if os.path.isdir("ww"):
                    compat_dirs = [
                        os.path.join("ww", name) for name in os.listdir("ww")
                        if os.path.isdir(os.path.join("ww", name)) and name.lower().startswith(pub)
                    ]

            compat_dirs = [directory for directory in compat_dirs if os.path.exists(directory)]
            if not compat_dirs:
                printStatus("miss", f"Could not find any installed directories for '{compat_target}'.", "warning")
                sys.exit(1)

            compat_total_files: int = 0
            compat_total_lines: int = 0
            for compat_dir in compat_dirs:
                files_changed, lines_changed = applyCompat(compat_dir, compat_mode, compat_custom_phrase)
                compat_total_files += files_changed
                compat_total_lines += lines_changed
            printStatus("done", f"Updated {compat_total_lines} line{'s' if compat_total_lines != 1 else ''} across {compat_total_files} file{'s' if compat_total_files != 1 else ''}.", "success")
        case "getinternal":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {NAME} getinternal <address> [version]", "warning")
                sys.exit(1)
            address = sys.argv[2]
            version = sys.argv[3] if len(sys.argv) > 3 else "latest"
            result = await installAsync(address, version, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
            if not result.exit_code:
                await installSubdependencies(address, version, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
        case "rminternal":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {NAME} rminternal <address> [version]", "warning")
                sys.exit(1)
            dist = sys.argv[2]
            printStatus("rm", f"Deleting {dist}", "info")
            if dist.strip() == "all":
                if os.path.isdir(INTERNAL_WW_DIR):
                    for entry in os.listdir(INTERNAL_WW_DIR):
                        if entry in ("len", "temp"):
                            continue
                        entry_path: str = os.path.join(INTERNAL_WW_DIR, entry)
                        if os.path.isdir(entry_path):
                            shutil.rmtree(entry_path)
                        else:
                            os.remove(entry_path)
                else:
                    printStatus("info", "No address installed.", "muted")
            else:
                if len(sys.argv) > 3:
                    rel = sys.argv[3]
                    deleted = removeAddressVersions(INTERNAL_WW_DIR, dist, rel)
                    if deleted:
                        printStatus("done", "Operation complete.", "success")
                    else:
                        printStatus("miss", f"Version '{rel}' of address '{dist.capitalize()}' is not installed here. Are you sure you spelled it right?", "warning")
                else:
                    deleted = removeAddressVersions(INTERNAL_WW_DIR, dist)
                    if deleted:
                        printStatus("done", "Operation complete.", "success")
                    else:
                        printStatus("miss", f"Address '{dist.capitalize()}' is not installed here. Are you sure you spelled it right?", "warning")
        case "getdepinternal":
            path = sys.argv[2] if len(sys.argv) > 2 else "."
            await getDepEverywhere(path, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
        case "stage":
            await handleStageCommand(sys.argv[2:])
        case "build":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} build <format(zip|targz|n2x|modm)> [source path] [output path]", "warning")
                sys.exit(1)
            await build(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".", sys.argv[4] if len(sys.argv) > 4 else "build.%")
        case "readme":
            if len(sys.argv) == 2:
                with open(os.path.join(os.path.dirname(__file__), "README.md")) as file:
                    print(file.read())
                sys.exit(0)
            ext_path: str = sys.argv[2] + ".n2x"
            with zipfile.ZipFile(os.path.join(EXTENSIONS_DIR, ext_path), "r") as zip_ref:
                zip_ref.extractall(ext_path.replace('.', '-'))
            with open(os.path.join(ext_path.replace('.', '-'), "README.md")) as file:
                print(file.read())
        case "license":
            if len(sys.argv) == 2:
                with open(os.path.join(os.path.dirname(__file__), "LICENSE.md")) as file:
                    print(file.read())
                sys.exit(0)
            ext_path: str = sys.argv[2] + ".n2x"
            with zipfile.ZipFile(os.path.join(EXTENSIONS_DIR, ext_path), "r") as zip_ref:
                zip_ref.extractall(ext_path.replace('.', '-'))
            with open(os.path.join(ext_path.replace('.', '-'), "LICENSE.md")) as file:
                print(file.read())
        case "trust-ext":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} trust-ext <extension>", "warning")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x"
            ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
            ext_dir_path: str = ext_path.replace('.', '-')
            trust(ext_filename, ext_dir_path)
        case "untrust-ext":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} untrust-ext <extension>", "warning")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x"
            with open(TRUSTED_EXTENSIONS_FILE) as file:
                content: str = file.read()
            with open(TRUSTED_EXTENSIONS_FILE, "w") as file:
                file.write("\n".join([line for line in content.split("\n") if line.strip() != ext_filename]))
        case "list-ext":
            printInstalledExtensions()
        case "load-len":
            loadLen()
        case "unload-len":
            unloadLen()
        case "install-ext":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} install-ext <extension>", "warning")
                sys.exit(1)
            loadLen()
            install_ext_filename: str = sys.argv[2] if sys.argv[2].endswith(".n2x") else sys.argv[2] + ".n2x"
            if os.path.exists(os.path.join(LEN_PATH, install_ext_filename)):
                shutil.copy(os.path.join(LEN_PATH, install_ext_filename), EXTENSIONS_DIR)
                printStatus("done", f"Extension '{sys.argv[2]}' installed successfully.", "success")
            else:
                printStatus("miss", f"Extension '{sys.argv[2]}' not found in the LEN repository.", "warning")
        case "uninstall-ext":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} uninstall-ext <extension>", "warning")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x" if not sys.argv[2].endswith(".n2x") else sys.argv[2]
            ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
            if os.path.exists(ext_path):
                os.remove(ext_path)
                printStatus("done", f"Extension '{sys.argv[2]}' uninstalled successfully.", "success")
            else:
                printStatus("miss", f"Extension '{sys.argv[2]}' not installed.", "warning")
        case "list-len":
            loadLen()
            printLenExtensions()
        case "help":
            printHelp()
            print()
            printExtensionCommands()
        case _:
            for ext_filename2 in [item for item in os.listdir(EXTENSIONS_DIR) if item.endswith(".n2x") or item.endswith(".n2xp")]:
                ext_path2: str = os.path.join(EXTENSIONS_DIR, ext_filename2)
                for ext_filename in [item for item in os.listdir(ext_path2) if item.endswith(".n2x")] if ext_filename2.endswith(".n2xp") else [ext_filename2]:
                    try:
                        if sys.argv[1] == ext_filename.removesuffix(".n2x"):
                            ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
                            ext_dir_path: str = ext_path.replace('.', '-')
                            with tarfile.open(ext_path, "r:gz") as tar:
                                tar.extractall(ext_dir_path)
                            trust(ext_filename, ext_dir_path)
                            script_path: str = os.path.join(ext_dir_path, "ext.py")
                            hydrodep_path: str = os.path.join(ext_dir_path, ".hydrodep")
                            if os.path.exists(hydrodep_path):
                                print("\033[94m", end="", flush=True)
                                await getDep(hydrodep_path, log=False)
                                print("\033[0m", end="", flush=True)
                            subprocess.run(["python", script_path, *sys.argv[2:]])
                            if os.path.exists(ext_dir_path):
                                shutil.rmtree(ext_dir_path)
                            if os.path.exists("ww"):
                                shutil.rmtree("ww")
                            return
                    except Exception:
                        for line in traceback.format_exc().split("\n"):
                            if line.strip():
                                print(cli(f"  {line}", CLI_ERROR))
            printStatus("miss", f"Unknown command: {sys.argv[1]}", "warning")
            print(f"Run {cli(f'{COMMAND} help', CLI_INFO)} for a list of commands.")
            
def entrypoint() -> None:
    asyncio.run(main())
    
if __name__ == "__main__":
    entrypoint()
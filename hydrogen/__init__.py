import sys, zipfile, shutil, os, json, subprocess, traceback, tarfile, asyncio, re, tempfile, platform, urllib, socket, inspect, urllib.request, urllib.error, logging
from dataclasses import dataclass, field
from urllib.request import urlretrieve

from .ww.mg26_11.config import getconf
from .ww.mg26_11.filepath import FilePath


SOURCEGEN_VERSION: str = "26.5" # SHOULD NOT BE CHANGED

NAME: str = "Hydrogen" # TODO
DESCRIPTION: str = "Sourcegen-based Distrobase installer." # TODO
VERSION: str = "26.2" # TODO
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
INTERNAL_WW_DIR: str = os.path.join(os.path.dirname(__file__), "ww")
INTERNAL_TEMP_DIR: str = os.path.join(INTERNAL_WW_DIR, "temp")
CONFIG_PATH: FilePath = FilePath(__file__) / ".." / "config.pyon"
DISTRO_NOT_FOUND_TEXT: str = "Distribution not found"
DSTBS_DIR: str = {
    "linux": "/var/lib",
    "windows": "C:\\ProgramData\\Distrobase",
    "darwin": "/Library/Application Support/Distrobase"
}[platform.system().lower()]

running_installs: dict[tuple[str, str], asyncio.Task] = {}

logger: logging.Logger = logging.getLogger(__name__)

class InvalidDistributionNameError(ValueError):
    """Raised when an address contains an invalid distribution name."""

class InvalidVersionError(ValueError):
    """Raised when an address contains an invalid release version."""

def getAddressInfo(address: str) -> dict:
    address = address.strip()
    if not address:
        raise ValueError("Address is empty.")
    home_registry: str = getconf("registry", "wednesware.org", config_path=CONFIG_PATH)
    addr_type: str = "registry" if "@" in address else ("local" if "#" in address else "")
    if not addr_type:
        addr_type = "local" if home_registry.startswith("#") else "registry"
    separator: str = "@" if addr_type == "registry" else "#"
    parts: list[str] = address.split(separator, maxsplit=1)
    if len(parts) == 1:
        parts.append(home_registry.removeprefix("#") if addr_type == "local" else home_registry)
    package_name: str = parts[0].strip()
    registry: str = parts[1].strip()
    version: str = "latest"
    if "=" in registry:
        registry, version = registry.split("=", maxsplit=1)
    elif "=" in package_name:
        package_name, version = package_name.split("=", maxsplit=1)
    package_parts: list[str] = package_name.split(".", maxsplit=1)
    if len(package_parts) == 2:
        author, distro = package_parts
    else:
        distro = package_parts[0]
        author = registry.split(".")[0].split(":")[0] if addr_type == "registry" else "localhost"
    if addr_type == "local" and not registry:
        registry = DSTBS_DIR
    return {
        "address": address,
        "author": author.lower(),
        "distro": distro.lower(),
        "registry": registry if addr_type == "local" else registry.lower(),
        "version": version,
        "type": addr_type
    }

@dataclass(slots=True)
class Result:
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
    printCommand("get <address>", "Download a distribution from an address.")
    printCommand("view <address>", "View information about a distribution.")
    printCommand("url <address>", "Get the URL of a tar.gz artifact via an address.")
    printCommand("fetch <address>", "Download a distribution to a temporary directory and print the extracted path.")
    printCommand("getlib <project> <address>", "Download a distribution into '<project>/libraries/author'.")
    printCommand("publish <project> <address>", "Publish a distribution from a project directory to a registry.")
    printCommand("rm <address>", "Delete one distribution or all installed distributions.")
    printCommand("getdep [path]", "Install missing dependencies from a .hydrodep file, including nested ones.")
    printCommand("forcegetdep [path]", "Install all dependencies, regardless of whether they are already installed from a .hydrodep file, including nested ones, forcing reinstallation of all dependencies.")
    printCommand("updlibs <project>", "Reinstall all distributions in '<project>/libraries' from their exact installed addresses.")
    printCommand("registry <registry>", "Set your home registry which will be used in operations when a registry is not specified.")
    print()
    printSection("Stage")
    printCommand("stage get <address>", "Stage a dependency install into ./ww.")
    printCommand("stage getlib <project> <address>", "Stage a library install into ./<project>/libraries/author.")
    printCommand("stage adddep <address>", "Stage adding one dependency line to ./.hydrodep.")
    printCommand("stage rmdep <address>", "Stage removing one dependency line from ./.hydrodep.")
    printCommand("stage getdep [target]", "Stage running getdep at ./<target>.")
    printCommand("stage forcegetdep [target]", "Stage running forcegetdep at ./<target>.")
    printCommand("stage updlibs [target]", "Stage running updlibs at ./<target>.")
    printCommand("stage rm <address>", "Stage dependency removal from ./ww.")
    printCommand("stage rmlib <project> <address>", "Stage library removal from ./<project>/libraries/author.")
    printCommand("stage publish <project> <address>", "Stage publishing a project distribution to a registry.")
    printCommand("stage registry <registry>", "Stage setting the home registry.")
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

def addressDirname(address: str, root: str = "distrobase") -> str:
    return os.path.join(root, address)

def dependencyFilePath(path: str) -> str:
    if path.endswith(".hydrodep"):
        return path
    return os.path.join(path, ".hydrodep")

def printResult(result: Result, color: bool = True) -> None:
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

def printDistroLocationError(address: str, exc: Exception) -> None:
    """Print a friendly CLI error and retain diagnostics in the debug log."""
    logger.debug("Could not locate distribution %r.", address, exc_info=exc)
    message: str = " ".join(
        line.strip() for line in str(exc).splitlines() if line.strip()
    ) or f"Could not locate distribution '{address}'."
    printStatus("fail", message, "error")

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
        "publish": "PUBLISH",
        "registry": "REGISTRY",
        "rm": "RM",
        "rmlib": "RMLIB",
        "cmd": "RUNCMD",
        "getinternal": "GETINTERNAL",
        "rminternal": "RMINTERNAL",
        "getdepinternal": "GETDEPINTERNAL",
    }.get(command.lower())


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

def localRegistryPath(registry: str) -> str:
    path: str = os.path.expanduser(registry)
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(os.getcwd(), path))
    return os.path.join(path, "dstbs")

def safeExtractZip(archive: str, destination: str) -> None:
    destination_abs: str = os.path.abspath(destination)
    with zipfile.ZipFile(archive) as archive_file:
        for member in archive_file.infolist():
            target: str = os.path.abspath(os.path.join(destination, member.filename))
            if os.path.commonpath((destination_abs, target)) != destination_abs:
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
        archive_file.extractall(destination)

def safeExtractTar(archive: str, destination: str) -> None:
    destination_abs: str = os.path.abspath(destination)
    with tarfile.open(archive, "r:*") as archive_file:
        for member in archive_file.getmembers():
            target: str = os.path.abspath(os.path.join(destination, member.name))
            if os.path.commonpath((destination_abs, target)) != destination_abs:
                raise RuntimeError(f"Unsafe archive member: {member.name}")
            if member.issym() or member.islnk():
                raise RuntimeError(f"Links are not allowed in archives: {member.name}")
        archive_file.extractall(destination)

def findLocalRelease(local_root: str, author: str, distro: str, version: str) -> tuple[str, str]:
    candidates: list[str] = []
    if version != "latest":
        candidates.extend([
            os.path.join(local_root, author, distro, version),
            os.path.join(local_root, author, distro, f"{version}.zip"),
            os.path.join(local_root, author, distro, f"{version}.tar"),
            os.path.join(local_root, author, distro, f"{version}.tar.gz"),
            os.path.join(local_root, author, distro, f"{version}.tgz"),
            os.path.join(local_root, f"{author}.{distro}", version),
        ])
    if version == "latest":
        candidates.extend([
            os.path.join(local_root, author, distro),
            os.path.join(local_root, f"{author}.{distro}"),
        ])
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        if version == "latest" and os.path.isdir(candidate):
            versions: list[str] = sorted(
                item for item in os.listdir(candidate)
                if os.path.isdir(os.path.join(candidate, item))
                or item.endswith((".zip", ".tar", ".tar.gz", ".tgz"))
            )
            if versions:
                selected: str = versions[-1]
                resolved: str = selected
                for suffix in (".tar.gz", ".tgz", ".zip", ".tar"):
                    resolved = resolved.removesuffix(suffix)
                return os.path.join(candidate, selected), resolved
        return candidate, version
    raise FileNotFoundError(
        f"Local distribution '{author}.{distro}={version}' was not found in '{local_root}'."
    )

def installLocalDistro(address: str, info: dict, install_root: str, reinstall: bool, work_dir: str) -> Result:
    local_root: str = localRegistryPath(info["registry"])
    source_path, resolved_version = findLocalRelease(
        local_root, info["author"], info["distro"], info["version"]
    )
    temporary_extract: str | None = None
    try:
        if os.path.isdir(source_path):
            source_root: str = source_path
        else:
            temporary_extract = tempfile.mkdtemp(prefix="hydrogen-local-", dir=work_dir)
            if source_path.endswith(".zip"):
                safeExtractZip(source_path, temporary_extract)
            elif source_path.endswith((".tar", ".tar.gz", ".tgz")):
                safeExtractTar(source_path, temporary_extract)
            else:
                raise RuntimeError(f"Unsupported local artifact: {source_path}")
            entries: list[str] = os.listdir(temporary_extract)
            source_root = (
                os.path.join(temporary_extract, entries[0])
                if len(entries) == 1 and os.path.isdir(os.path.join(temporary_extract, entries[0]))
                else temporary_extract
            )

        if os.path.exists(install_root) and os.listdir(install_root) and not reinstall:
            return Result(
                status="error",
                lines=[f"Distro is already installed at {install_root}"],
                message=f"Distro is already installed at {install_root}",
                exit_code=1,
            )

        parent: str = os.path.dirname(os.path.abspath(install_root))
        os.makedirs(parent, exist_ok=True)
        staged_root: str = tempfile.mkdtemp(prefix=".hydrogen-install-", dir=parent)
        try:
            for name in os.listdir(source_root):
                source: str = os.path.join(source_root, name)
                destination: str = os.path.join(staged_root, name)
                if os.path.isdir(source):
                    shutil.copytree(source, destination, symlinks=True)
                else:
                    shutil.copy2(source, destination)
            if os.path.exists(install_root):
                shutil.rmtree(install_root)
            os.replace(staged_root, install_root)
        except Exception:
            shutil.rmtree(staged_root, ignore_errors=True)
            raise

        return Result(
            status="success",
            success=True,
            lines=[f"Installed {address} release {resolved_version} to {install_root}"],
            message=f"Installed {address} release {resolved_version} to {install_root}",
            exit_code=0,
        )
    finally:
        if temporary_extract:
            shutil.rmtree(temporary_extract, ignore_errors=True)


def registryBaseUrl(registry: str) -> str:
    """Build the API base URL for a registry address."""
    normalized: str = registry.strip()
    if normalized.startswith(("http://", "https://")):
        return normalized.rstrip("/")
    if normalized.startswith(("127.0.0.1", "localhost")):
        return f"http://{normalized}".rstrip("/")
    return f"https://dstbs.{normalized}".rstrip("/")


def registryNetworkError(address: str, registry: str, exc: Exception) -> Result:
    error_text: str = str(exc)
    reason = getattr(exc, "reason", None)
    reason_text = str(reason or exc).lower()
    if isinstance(reason, socket.gaierror) or any(
        token in reason_text
        for token in (
            "name or service not known",
            "temporary failure in name resolution",
            "no address associated with hostname",
            "nodename nor servname provided",
        )
    ):
        message: str = (
            f"Registry '{registryBaseUrl(registry)}' could not be resolved. "
            f"Check DNS, internet access, or configure another registry with "
            f"'{COMMAND} registry <registry>'."
        )
    elif "not found" in reason_text:
        address_info: dict = getAddressInfo(address)
        message = f"Distribution '{address_info['author']}.{address_info['distro']}' was not found in registry '{address_info['registry']}'."
    else:
        message = f"Failed to contact registry '{registryBaseUrl(registry)}': {error_text}"
    return Result(
        status="error",
        success=False,
        lines=[f"Failed to install {address}: {message}"],
        message=message,
        exit_code=1,
    )

def findDistroLocation(address: str) -> str:
    info: dict = getAddressInfo(address)
    author: str = info["author"]
    distro: str = info["distro"]
    version: str = info["version"]

    name_pattern: str = r"[a-z0-9][a-z0-9_-]*"
    invalid_names: list[str] = [
        name for name in (author, distro)
        if not re.fullmatch(name_pattern, name)
    ]
    if invalid_names:
        raise InvalidDistributionNameError(
            f"Invalid distribution name '{author}.{distro}'."
        )

    if (
        not version
        or version != "latest"
        and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", version)
    ):
        raise InvalidVersionError(
            f"Invalid version '{version}'. Use 'latest' or a version containing only letters, numbers, '.', '_' and '-'."
        )

    display_name: str = f"{author}.{distro}={version}"

    if info["type"] == "local":
        local_root: str = localRegistryPath(info["registry"])
        try:
            source_path, resolved_version = findLocalRelease(
                local_root, author, distro, version
            )
        except FileNotFoundError as exc:
            distribution_paths: list[str] = [
                os.path.join(local_root, author, distro),
                os.path.join(local_root, f"{author}.{distro}"),
            ]
            if not any(os.path.exists(path) for path in distribution_paths):
                raise FileNotFoundError(
                    f"Could not find distribution '{author}.{distro}#'."
                ) from exc
            if version != "latest":
                raise FileNotFoundError(
                    f"Could not find version '{version}' of distribution '{author}.{distro}#'."
                ) from exc
            raise FileNotFoundError(
                f"Distribution: {display_name}\n"
                f"Registry: {local_root}\n"
                "Reason: no matching release was found."
            ) from exc
        if os.path.isdir(source_path):
            raise FileNotFoundError(
                f"Distribution: {author}.{distro}={resolved_version}\n"
                f"Found: {source_path}\n"
                "Reason: a release archive is required.\n"
                "Expected: .tar.gz or .tgz"
            )
        if not source_path.endswith((".tar.gz", ".tgz")):
            raise FileNotFoundError(
                f"Distribution: {author}.{distro}={resolved_version}\n"
                f"Found: {source_path}\n"
                "Reason: the release format is unsupported.\n"
                "Expected: .tar.gz or .tgz"
            )
        return os.path.abspath(source_path)

    base_url: str = registryBaseUrl(info["registry"])
    distribution_url: str = (
        f"{base_url}/v1/{urllib.parse.quote(author)}/"
        f"{urllib.parse.quote(distro)}"
    )
    lookup_stage: str = "distribution"
    try:
        with urllib.request.urlopen(distribution_url) as response:
            distribution: dict = json.load(response)
        resolved_version = version if version != "latest" else distribution["latest"]
        release_url: str = f"{distribution_url}/{urllib.parse.quote(resolved_version)}"
        lookup_stage = "release"
        with urllib.request.urlopen(release_url) as response:
            release: dict = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            if lookup_stage == "release":
                raise FileNotFoundError(
                    f"Version '{resolved_version}' was not found for distribution '{author}.{distro}'."
                ) from exc
            raise FileNotFoundError(
                f"Distribution '{author}.{distro}' was not found in registry '{info['registry']}'."
            ) from exc
        raise RuntimeError(
            f"Registry '{info['registry']}' returned HTTP {exc.code} while looking up '{display_name}'."
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not contact registry '{registryBaseUrl(info['registry'])}' while looking up '{display_name}': {exc.reason}"
        ) from exc
    artifacts: list = release.get("artifacts", [])
    for artifact in artifacts:
        artifact_name: str = artifact.get("name", "")
        if artifact_name.endswith((".tar.gz", ".tgz")):
            return f"{release_url}/{urllib.parse.quote(artifact_name)}"
    raise FileNotFoundError(
        f"Could not find an archive for '{author}.{distro}={resolved_version}' in registry '{info['registry']}'.\n"
        "  Expected: a .tar.gz or .tgz artifact"
    )


def viewDistro(address: str) -> Result:
    info = getAddressInfo(address)
    author = info["author"]
    distro = info["distro"]
    version = info["version"]

    try:
        if info["type"] == "local":
            source_path, resolved_version = findLocalRelease(
                localRegistryPath(info["registry"]), author, distro, version
            )
            artifact_name = "<directory>" if os.path.isdir(source_path) else os.path.basename(source_path)
            artifact_size = "directory" if os.path.isdir(source_path) else f"{os.path.getsize(source_path)} bytes"
            lines = [
                f"Distribution: {author}.{distro}",
                f"Release: {resolved_version}",
                f"Registry: {info['registry']}",
                f"Artifact: {artifact_name}",
                f"Size: {artifact_size}",
            ]
        else:
            base_url = registryBaseUrl(info["registry"])
            distribution_url = (
                f"{base_url}/v1/{urllib.parse.quote(author)}/"
                f"{urllib.parse.quote(distro)}"
            )
            with urllib.request.urlopen(distribution_url) as response:
                distribution = json.load(response)
            resolved_version = version if version != "latest" else distribution["latest"]
            release_url = f"{distribution_url}/{urllib.parse.quote(resolved_version)}"
            with urllib.request.urlopen(release_url) as response:
                release = json.load(response)
            artifacts = release.get("artifacts", [])
            lines = [
                f"Distribution: {release.get('author', author)}.{release.get('distribution', distro)}",
                f"Release: {release.get('release', resolved_version)}",
                f"Registry: {info['registry']}",
                f"Artifacts: {len(artifacts)}",
            ]
            for artifact in artifacts:
                lines.extend([
                    f"Artifact: {artifact.get('name', '<unnamed>')}",
                    f"Size: {artifact.get('size', 0)} bytes",
                    f"SHA-256: {artifact.get('sha256', '')}",
                ])

        return Result(
            status="success",
            success=True,
            lines=lines,
            message=f"Viewed {author}.{distro} release {resolved_version}",
            exit_code=0,
        )
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        if DISTRO_NOT_FOUND_TEXT in detail:
            message = f"Distribution '{author}.{distro}' was not found in registry '{info['registry']}'."
        else:
            message = f"Registry returned HTTP {exc.code}: {detail}"
        return Result(
            status="error",
            success=False,
            lines=[message],
            message=message,
            exit_code=1,
        )
    except urllib.error.URLError as exc:
        network_error = registryNetworkError(address, info["registry"], exc)
        return Result(
            status="error",
            success=False,
            lines=[f"Failed to view {address}: {network_error.message}"],
            message=network_error.message,
            exit_code=1,
        )
    except Exception as exc:
        message = f"Failed to view {address}: {exc}"
        return Result(status="error", success=False, lines=[message], message=message, exit_code=1)


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
        "ADDDEP": 1,
        "ADDLIB": 2,
        "ADDNDEP": 1,
        "RMNDEP": 1,
        "GETDEP": 1,
        "FORCEGETDEP": 1,
        "UPDLIBS": 1,
        "PUBLISH": 2,
        "REGISTRY": 1,
        "RMDEP": 1,
        "RMLIB": 2,
        "GETINTERNAL": 1,
        "RMINTERNAL": 1,
        "GETDEPINTERNAL": 1,
    }
    if action not in arity:
        return None
    if len(args) != arity[action]:
        return None
    return StageAction(action, args, line)


def updateHomeRegistry(registry: str) -> None:
    config_data: dict = {}
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH) as config_file:
            config_data = json.load(config_file)
    config_data["registry"] = registry
    with open(CONFIG_PATH, "w") as config_file:
        json.dump(config_data, config_file, indent=4)
        config_file.write("\n")


def runStagedCommand(command: str) -> None:
    printStatus("cmd", command, "info")
    result: subprocess.CompletedProcess = subprocess.run(command, shell=True, cwd=os.getcwd())
    if result.returncode != 0:
        printStatus("fail", f"Command failed with exit code {result.returncode}: {command}", "error")
        raise SystemExit(result.returncode)

def queueInstallToRoot(address: str, emit: bool = True, install_root: str = "distrobase", reinstall: bool = True, work_dir: str = ".") -> asyncio.Task:
    install_root = os.path.join(
        install_root,
        getAddressInfo(address)["distro"].lower(),
    )
    resolved_address: str = address
    key: tuple[str, str] = (resolved_address.lower(), os.path.realpath(install_root))
    if key in running_installs:
        if emit:
            printStatus("wait", f"Already queued {resolved_address.lower()} -> {install_root}", "muted")
        return running_installs[key]

    if emit:
        printStatus("queue", f"{resolved_address.lower()} -> {install_root}", "info")
    task: asyncio.Task = asyncio.create_task(asyncio.to_thread(installDistroToRoot, resolved_address, install_root, reinstall, work_dir))
    running_installs[key] = task

    def cleanup(completed_task: asyncio.Task, install_key: tuple[str, str] = key) -> None:
        if running_installs.get(install_key) is completed_task:
            running_installs.pop(install_key, None)

    task.add_done_callback(cleanup)
    return task


async def executeStageOrdered(actions: list[StageAction]) -> None:
    for action in actions:
        if action.action == "ADDDEP":
            address = action.args[0]
            result: Result = await queueInstallToRoot(address, True, "distrobase", True)
            printResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        elif action.action == "ADDLIB":
            project, address = action.args
            install_root: str = os.path.join(project, "libraries", "distrobase")
            result = await queueInstallToRoot(address, True, install_root, True)
            printResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        elif action.action == "ADDNDEP":
            address = action.args[0]
            if addHydrodepDependency(".", address):
                printStatus("done", f"Added dependency '{address}' to ./.hydrodep.", "success")
            else:
                printStatus("info", f"Dependency '{address}' is already in ./.hydrodep.", "muted")
        elif action.action == "RMNDEP":
            address = action.args[0]
            if removeHydrodepDependency(".", address):
                printStatus("done", f"Removed dependency '{address}' from ./.hydrodep.", "success")
            else:
                printStatus("miss", f"Dependency '{address}' was not found in ./.hydrodep.", "warning")
        elif action.action == "GETDEP":
            target = action.args[0]
            await getDepEverywhere(target)
        elif action.action == "GETDEPINTERNAL":
            target = action.args[0]
            await getDepEverywhere(target, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
        elif action.action == "FORCEGETDEP":
            target = action.args[0]
            await getDepEverywhere(target, force=True)
        elif action.action == "UPDLIBS":
            project = action.args[0]
            await reinstallProjectLibraries(project)
        elif action.action == "GETINTERNAL":
            address = action.args[0]
            result = await installAsync(address, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
            printResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
            await installSubdependencies(address, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
        elif action.action == "RMINTERNAL":
            address = action.args[0]
            deleted: int = removeAddressVersions(INTERNAL_WW_DIR, address)
            printStatus("done", f"Removed {deleted} installed copy{'ies' if deleted != 1 else ''} of '{address}' from {INTERNAL_WW_DIR}.", "success")
        elif action.action == "RMDEP":
            address = action.args[0]
            deleted: int = removeAddressVersions("distrobase", address)
            printStatus("done", f"Removed {deleted} installed copy{'ies' if deleted != 1 else ''} of '{address}' from ./ww.", "success")
        elif action.action == "RMLIB":
            project, address = action.args
            install_root = os.path.join(project, "libraries", "ww")
            deleted = removeAddressVersions(install_root, address)
            printStatus("done", f"Removed {deleted} installed copy{'ies' if deleted != 1 else ''} of '{address}' from ./{project}/libraries/ww.", "success")
        elif action.action == "PUBLISH":
            project, address = action.args
            result = await publishDistro(project, address)
            printResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        elif action.action == "REGISTRY":
            registry = action.args[0]
            updateHomeRegistry(registry)
            printStatus("done", f"Home registry set to '{registry}'.", "success")
        elif action.action == "RUNCMD":
            runStagedCommand(action.args[0])


async def commitStageBatched(actions: list[StageAction]) -> None:
    add_dep: list[str] = []
    add_lib: list[tuple[str, str]] = []
    rm_dep: list[str] = []
    rm_lib: list[tuple[str, str]] = []

    for action in actions:
        if action.action == "ADDDEP":
            add_dep.append(action.args[0])
        elif action.action == "ADDLIB":
            add_lib.append((action.args[0], action.args[1]))
        elif action.action == "RMDEP":
            rm_dep.append(action.args[0])
        elif action.action == "RMLIB":
            rm_lib.append((action.args[0], action.args[1]))

    add_dep_address: set[str] = set(add_dep)
    rm_dep_address: set[str] = set(rm_dep)
    dep_conflicts: set[str] = add_dep_address & rm_dep_address
    if dep_conflicts:
        text: str = ", ".join(sorted(dep_conflicts))
        printStatus("fail", f"Cannot commit: adddep and rmdep conflict for {text}", "error")
        raise SystemExit(1)

    add_lib_address: set[tuple[str, str]] = set(add_lib)
    rm_lib_address: set[tuple[str, str]] = set(rm_lib)
    lib_conflicts: set[tuple[str, str]] = add_lib_address & rm_lib_address
    if lib_conflicts:
        text = ", ".join(f"{project}:{address}" for project, address in sorted(lib_conflicts))
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
        elif action.action == "PUBLISH":
            project, address = action.args
            result = await publishDistro(project, address)
            printResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        elif action.action == "REGISTRY":
            registry = action.args[0]
            updateHomeRegistry(registry)
            printStatus("done", f"Home registry set to '{registry}'.", "success")
        elif action.action == "ADDNDEP":
            address = action.args[0]
            if addHydrodepDependency(".", address):
                printStatus("done", f"Added dependency '{address}' to ./.hydrodep.", "success")
            else:
                printStatus("info", f"Dependency '{address}' is already in ./.hydrodep.", "muted")
        elif action.action == "RMNDEP":
            address = action.args[0]
            if removeHydrodepDependency(".", address):
                printStatus("done", f"Removed dependency '{address}' from ./.hydrodep.", "success")
            else:
                printStatus("miss", f"Dependency '{address}' was not found in ./.hydrodep.", "warning")
        elif action.action == "GETDEP":
            target = action.args[0]
            await getDepEverywhere(target)
        elif action.action == "GETDEPINTERNAL":
            target = action.args[0]
            await getDepEverywhere(target, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
        elif action.action == "FORCEGETDEP":
            target = action.args[0]
            await getDepEverywhere(target, force=True)
        elif action.action == "UPDLIBS":
            project = action.args[0]
            await reinstallProjectLibraries(project)
        elif action.action == "GETINTERNAL":
            address = action.args[0]
            result = await installAsync(address, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
            if result.exit_code:
                printResult(result)
                raise SystemExit(result.exit_code)
            printResult(result)
            await installSubdependencies(address, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
    if command_failures:
        raise SystemExit(command_failures)

    install_tasks: list[asyncio.Task] = []
    for address in add_dep:
        install_tasks.append(queueInstallToRoot(address, True, "distrobase", True))
    for project, address in add_lib:
        install_tasks.append(queueInstallToRoot(address, True, os.path.join(project, "libraries", "distrobase"), True, "."))

    if install_tasks:
        install_results: list[Result] = await asyncio.gather(*install_tasks)
        install_failures: int = 0
        for result in install_results:
            printResult(result)
            install_failures += int(bool(result.exit_code))
        if install_failures:
            printStatus("fail", f"Commit install finished with {install_failures} failure{'s' if install_failures != 1 else ''}.", "error")
            raise SystemExit(1)

    for address in rm_dep:
        deleted: int = removeAddressVersions("distrobase", address)
        printStatus("done", f"Removed {deleted} installed copy{'ies' if deleted != 1 else ''} of '{address}' from ./ww.", "success")
    for project, address in rm_lib:
        install_root: str = os.path.join(project, "libraries", "distrobase")
        deleted = removeAddressVersions(install_root, address)
        printStatus("done", f"Removed {deleted} installed copy{'ies' if deleted != 1 else ''} of '{address}' from ./{project}/libraries/ww.", "success")


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
        printStatus("help", f"Usage: {COMMAND} stage <get|getlib|adddep|rmdep|getdep|forcegetdep|updlibs|rm|rmlib|cmd|getinternal|rminternal|getdepinternal|cancel|execute|commit> [...]", "warning")
        sys.exit(1)

    subcommand: str = args[0].lower()

    if subcommand == "get":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage get <address>", "warning")
            sys.exit(1)
        address: str = args[1]
        appendStageLine(f"ADDDEP|{address}")
        printStatus("stage", f"Staged get {address}", "success")
        return

    if subcommand == "getlib":
        if len(args) < 3:
            printStatus("help", f"Usage: {COMMAND} stage getlib <project> <address>", "warning")
            sys.exit(1)
        project: str = args[1]
        address = args[2]
        appendStageLine(f"ADDLIB|{project}|{address}")
        printStatus("stage", f"Staged getlib {project} {address}", "success")
        return

    if subcommand == "adddep":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage adddep <address>", "warning")
            sys.exit(1)
        address = args[1]
        appendStageLine(f"ADDNDEP|{address}")
        printStatus("stage", f"Staged adddep {address}", "success")
        return

    if subcommand == "rmdep":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage rmdep <address>", "warning")
            sys.exit(1)
        address = args[1]
        appendStageLine(f"RMNDEP|{address}")
        printStatus("stage", f"Staged rmdep {address}", "success")
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
            printStatus("help", f"Usage: {COMMAND} stage rm <address>", "warning")
            sys.exit(1)
        address = args[1]
        appendStageLine(f"RMDEP|{address}")
        printStatus("stage", f"Staged rm {address}", "success")
        return

    if subcommand == "rmlib":
        if len(args) < 3:
            printStatus("help", f"Usage: {COMMAND} stage rmlib <project> <address>", "warning")
            sys.exit(1)
        project: str = args[1]
        address = args[2]
        appendStageLine(f"RMLIB|{project}|{address}")
        printStatus("stage", f"Staged rmlib {project} {address}", "success")
        return

    if subcommand == "getinternal":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage getinternal <address>", "warning")
            sys.exit(1)
        address = args[1]
        appendStageLine(f"GETINTERNAL|{address}")
        printStatus("stage", f"Staged getinternal {address}", "success")
        return

    if subcommand == "rminternal":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage rminternal <address>", "warning")
            sys.exit(1)
        address = args[1]
        appendStageLine(f"RMINTERNAL|{address}")
        printStatus("stage", f"Staged rminternal {address}", "success")
        return

    if subcommand == "getdepinternal":
        if len(args) > 2:
            printStatus("help", f"Usage: {COMMAND} stage getdepinternal [target]", "warning")
            sys.exit(1)
        target = args[1] if len(args) > 1 else "."
        appendStageLine(f"GETDEPINTERNAL|{target}")
        printStatus("stage", f"Staged getdepinternal {target}", "success")
        return

    if subcommand == "publish":
        if len(args) < 3:
            printStatus("help", f"Usage: {COMMAND} stage publish <project> <address>", "warning")
            sys.exit(1)
        project: str = args[1]
        address: str = args[2]
        appendStageLine(f"PUBLISH|{project}|{address}")
        printStatus("stage", f"Staged publish {project} {address}", "success")
        return

    if subcommand == "registry":
        if len(args) < 2:
            printStatus("help", f"Usage: {COMMAND} stage registry <registry>", "warning")
            sys.exit(1)
        registry: str = " ".join(args[1:])
        appendStageLine(f"REGISTRY|{registry}")
        printStatus("stage", f"Staged registry {registry}", "success")
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
            printStatus("help", f"Usage: {COMMAND} stage cancel [get|getlib|adddep|rmdep|getdep|forcegetdep|updlibs|publish|registry|rm|rmlib|cmd|getinternal|rminternal|getdepinternal|last] [args]", "warning")
            sys.exit(1)

        target_line: str | None = None
        if tag == "GET":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel get <address>", "warning")
                sys.exit(1)
            address: str = args[2]
            target_line = f"ADDDEP|{address}"
        elif tag == "GETLIB":
            if len(args) < 4:
                printStatus("help", f"Usage: {COMMAND} stage cancel getlib <project> <address>", "warning")
                sys.exit(1)
            project = args[2]
            address = args[3]
            target_line = f"ADDLIB|{project}|{address}"
        elif tag == "ADDDEP":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel adddep <address>", "warning")
                sys.exit(1)
            address = args[2]
            target_line = f"ADDNDEP|{address}"
        elif tag == "RMDEP":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel rmdep <address>", "warning")
                sys.exit(1)
            address = args[2]
            target_line = f"RMNDEP|{address}"
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
                printStatus("help", f"Usage: {COMMAND} stage cancel rm <address>", "warning")
                sys.exit(1)
            address = args[2]
            target_line = f"RMDEP|{address}"
        elif tag == "RMLIB":
            if len(args) < 4:
                printStatus("help", f"Usage: {COMMAND} stage cancel rmlib <project> <address>", "warning")
                sys.exit(1)
            project = args[2]
            address = args[3]
            target_line = f"RMLIB|{project}|{address}"
        elif tag == "PUBLISH":
            if len(args) < 4:
                printStatus("help", f"Usage: {COMMAND} stage cancel publish <project> <address>", "warning")
                sys.exit(1)
            project = args[2]
            address = args[3]
            target_line = f"PUBLISH|{project}|{address}"
        elif tag == "REGISTRY":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel registry <registry>", "warning")
                sys.exit(1)
            registry = " ".join(args[2:])
            target_line = f"REGISTRY|{registry}"
        elif tag == "RUNCMD":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel cmd <command>", "warning")
                sys.exit(1)
            command = " ".join(args[2:])
            target_line = f"RUNCMD|{command}"
        elif tag == "GETINTERNAL":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel getinternal <address>", "warning")
                sys.exit(1)
            address = args[2]
            target_line = f"GETINTERNAL|{address}"
        elif tag == "RMINTERNAL":
            if len(args) < 3:
                printStatus("help", f"Usage: {COMMAND} stage cancel rminternal <address>", "warning")
                sys.exit(1)
            address = args[2]
            target_line = f"RMINTERNAL|{address}"
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
    printStatus("help", f"Usage: {COMMAND} stage <get|getlib|adddep|rmdep|getdep|forcegetdep|updlibs|publish|registry|rm|rmlib|cmd|getinternal|rminternal|getdepinternal|cancel|execute|commit> [...]", "warning")
    sys.exit(1)
    
async def reinstallProjectLibraries(project: str) -> None:
    install_root: str = os.path.join(project, "libraries")
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
        tasks.append(queueInstallToRoot(pub, True, install_root, True, "."))

    if not tasks:
        printStatus("miss", "No reinstallable libraries were found.", "warning")
        if ignored:
            printStatus("info", f"Ignored {ignored} unrecognized directory(ies).", "muted")
        return

    results: list[Result] = await asyncio.gather(*tasks)
    failures: int = 0
    for result in results:
        printResult(result)
        failures += int(bool(result.exit_code))
    if failures:
        printStatus("fail", f"Library reinstall finished with {failures} failure{'s' if failures != 1 else ''}.", "error")
        raise SystemExit(1)

    printStatus("done", f"Reinstalled {len(results)} librar{'y' if len(results) == 1 else 'ies'} from {install_root}.", "success")

def installDistro(address: str, reinstall: bool = True) -> Result:
    return installDistroToRoot(address, os.path.join("", getAddressInfo(address)['author'], getAddressInfo(address)['distro']), reinstall)

def installDistroToRoot(address: str, install_root: str = "distrobase", reinstall: bool = True, work_dir: str = ".") -> Result:
    info = getAddressInfo(address)
    install_root = os.path.abspath(install_root)
    work_dir = os.path.abspath(work_dir)
    os.makedirs(install_root, exist_ok=True)
    os.makedirs(work_dir, exist_ok=True)
    if info["type"] == "local":
        try:
            return installLocalDistro(address, info, install_root, reinstall, work_dir)
        except Exception as exc:
            return Result(
                status="error",
                success=False,
                lines=[f"Failed to install {address}: {exc}"],
                message=f"Failed to install {address}: {exc}",
                exit_code=1,
            )
    registry: str = info["registry"]
    base_url: str = registryBaseUrl(registry)
    author = info["author"]
    distro = info["distro"]
    version = info["version"]
    temp_dir = tempfile.mkdtemp(
        prefix="hydrogen-install-",
        dir=work_dir,
    )
    try:
        if version == "latest":
            distribution_url = (
                f"{base_url}/v1/"
                f"{author}/{distro}"
            )
            with urllib.request.urlopen(
                distribution_url
            ) as response:
                distribution = json.load(response)
            version = distribution["latest"]
        release_url = (
            f"{base_url}/v1/"
            f"{author}/{distro}/{version}"
        )
        with urllib.request.urlopen(
            release_url
        ) as response:
            release = json.load(response)
        artifacts = release.get("artifacts", [])
        if not artifacts:
            raise RuntimeError(
                f"Release {version} contains no artifacts."
            )
        artifact = artifacts[0]
        artifact_name = artifact["name"]
        if (
            os.path.basename(artifact_name)
            != artifact_name
        ):
            raise RuntimeError(
                f"Invalid artifact name: {artifact_name}"
            )
        archive = os.path.join(
            temp_dir,
            artifact_name,
        )
        artifact_url = (
            f"{base_url}/v1/"
            f"{author}/{distro}/{version}/"
            f"{urllib.parse.quote(artifact_name)}"
        )
        with urllib.request.urlopen(
            artifact_url
        ) as response:
            with open(archive, "wb") as file:
                shutil.copyfileobj(response, file)
        extracted = os.path.join(
            temp_dir,
            "extracted",
        )
        os.makedirs(extracted, exist_ok=True)
        if artifact_name.endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extracted)
        elif artifact_name.endswith((
            ".tar.gz",
            ".tgz",
            ".tar",
        )):
            with tarfile.open(
                archive,
                "r:*",
            ) as tf:

                tf.extractall(extracted)
        else:
            raise RuntimeError(
                f"Unsupported artifact format: "
                f"{artifact_name}"
            )
        entries = os.listdir(extracted)
        if (
            len(entries) == 1
            and os.path.isdir(
                os.path.join(extracted, entries[0])
            )
        ):
            source_root = os.path.join(
                extracted,
                entries[0],
            )
        else:
            source_root = extracted
        if os.path.exists(install_root) and os.listdir(
            install_root
        ):
            if not reinstall:
                return Result(
                    status="error",
                    success=False,
                    message=(
                        f"Address is already installed "
                        f"at {install_root}"
                    ),
                    lines=[
                        (
                            f"Address is already installed "
                            f"at {install_root}"
                        )
                    ],
                    exit_code=1,
                )
            for name in os.listdir(install_root):
                path = os.path.join(
                    install_root,
                    name,
                )
                if (
                    os.path.isdir(path)
                    and not os.path.islink(path)
                ):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        for name in os.listdir(source_root):
            source = os.path.join(
                source_root,
                name,
            )
            destination = os.path.join(
                install_root,
                name,
            )
            shutil.move(
                source,
                destination,
            )
        return Result(
            status="success",
            success=True,
            lines=[
                (
                    f"Installed {address} "
                    f"release {version} "
                    f"to {install_root}"
                )
            ],
            message=(
                f"Installed {address} "
                f"release {version} "
                f"to {install_root}"
            ),
            exit_code=0,
        )
    except urllib.error.URLError as exc:
        return registryNetworkError(address, registry, exc)
    except Exception as exc:
        if os.path.exists(install_root):
            for name in os.listdir(install_root):
                path = os.path.join(
                    install_root,
                    name,
                )
                if (
                    os.path.isdir(path)
                    and not os.path.islink(path)
                ):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        return Result(
            status="error",
            success=False,
            lines=[
                f"Failed to install {address}: {exc}"
            ],
            message=(
                f"Failed to install {address}: {exc}"
            ),
            exit_code=1,
        )
    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

def queueInstall(address: str, emit: bool = True, reinstall: bool = True, install_root: str = "distrobase", work_dir: str = ".") -> asyncio.Task:
    return queueInstallToRoot(address, emit, install_root, reinstall, work_dir)

async def installAsync(address: str, reinstall: bool = True, color: bool = True, emit: bool = True, fatal: bool = True, install_root: str = "distrobase", work_dir: str = ".") -> Result:
    result: Result = await queueInstallToRoot(
        address,
        emit,
        install_root,
        reinstall,
        work_dir,
    )
    if emit:
        printResult(result, color)
    if fatal and result.exit_code:
        raise SystemExit(result.exit_code)
    return result


async def getdepRecursive(path: str, color: bool = True, emit: bool = True, visited: set[str] | None = None, installed: set[str] | None = None, force: bool = False, install_root: str = "distrobase", work_dir: str = ".") -> None:
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
        if emit:
            printStatus("done", "No dependencies needed.", "success")
        return
    if emit:
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
    if emit and print_tip:
        printStatus("deny", "To allow scripts, re-run with '--allow'. To skip scripts, re-run with '--skip'.", "info")
    tasks: list[asyncio.Task] = [queueInstall(address, emit, force, install_root, work_dir) for address in pending_deps]
    results: list[Result] = await asyncio.gather(*tasks)
    for result in results:
        printResult(result, color)

    failures: int = sum(1 for result in results if result.exit_code)
    if failures:
        if emit:
            printStatus("fail", f"Dependency install finished with {failures} failure{'s' if failures != 1 else ''}.", "error")
        raise SystemExit(1)

    for address in deps:
        installed_dep_path: str = dependencyFilePath(addressDirname(address, install_root))
        await getdepRecursive(installed_dep_path, color=color, log=False, visited=visited, installed=installed, install_root=install_root, work_dir=work_dir)
    if emit:
        printStatus("done", "All dependencies are ready.", "success")


async def getDep(path: str, color: bool = True, emit: bool = True, force: bool = False, install_root: str = "distrobase", work_dir: str = ".") -> None:
    await getdepRecursive(path, color=color, emit=emit, force=force, install_root=install_root, work_dir=work_dir)


async def getDepEverywhere(path: str, color: bool = True, force: bool = False, install_root: str = "distrobase", work_dir: str = ".") -> None:
    dep_files: list[str] = findHydrodepFiles(path)
    if not dep_files:
        printStatus("miss", f"No .hydrodep files found under '{path}'.", "warning")
        return

    printStatus("deps", f"Found {len(dep_files)} .hydrodep file{'s' if len(dep_files) != 1 else ''} under '{path}'.", "info")
    visited: set[str] = set()
    installed: set[str] = set()
    for dep_file in dep_files:
        await getdepRecursive(dep_file, color=color, emit=True, visited=visited, installed=installed, force=force, install_root=install_root, work_dir=work_dir)


async def installSubdependencies(address: str, color: bool = True, emit: bool = True, install_root: str = "distrobase", work_dir: str = ".") -> None:
    resolved_address: str = address
    dep_path: str = dependencyFilePath(addressDirname(resolved_address, install_root))
    if emit:
        printStatus("deps", f"Checking sub-dependencies for {resolved_address}", "info")
    if not os.path.isfile(dep_path):
        if emit:
            printStatus("info", "No sub-dependencies declared.", "muted")
        return
    await getDep(dep_path, color=color, emit=emit, install_root=install_root, work_dir=work_dir)
        
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
        
async def publishDistro(
    project_path: str,
    address: str,
) -> Result:

    try:
        project_path = os.path.abspath(
            os.path.expanduser(project_path)
        )

        if not os.path.isdir(project_path):
            return Result(
                status="error",
                success=False,
                lines=[
                    f"Project directory not found: {project_path}"
                ],
                message=(
                    f"Project directory not found: "
                    f"{project_path}"
                ),
                exit_code=1,
            )

        info = getAddressInfo(address)

        if info["type"] != "registry" and info["type"] != "local":
            return Result(
                status="error",
                success=False,
                lines=[
                    f"Unsupported publish address: {address}"
                ],
                message=(
                    f"Unsupported publish address: {address}"
                ),
                exit_code=1,
            )

        author = info["author"]
        distro = info["distro"]
        version = info["version"]

        if version == "latest":
            return Result(
                status="error",
                success=False,
                lines=[
                    "A release version is required when publishing."
                ],
                message=(
                    "A release version is required when publishing."
                ),
                exit_code=1,
            )

        temp_dir = tempfile.mkdtemp(
            prefix="hydrogen-publish-"
        )

        try:
            # ---------------------------------------------------------
            # Build artifact
            # ---------------------------------------------------------

            archive = os.path.join(
                temp_dir,
                f"{version}.tar.gz",
            )

            printStatus(
                "build",
                f"Building project into {archive}...",
                "info",
            )

            with tarfile.open(
                archive,
                "w:gz",
            ) as tar:

                for root, dirs, files in os.walk(
                    project_path
                ):
                    dirs[:] = [
                        directory
                        for directory in dirs
                        if directory not in {
                            ".git",
                            "__pycache__",
                            ".venv",
                            "venv",
                            "node_modules",
                        }
                    ]

                    for file_name in files:
                        file_path = os.path.join(
                            root,
                            file_name,
                        )

                        if os.path.abspath(
                            file_path
                        ) == os.path.abspath(
                            archive
                        ):
                            continue

                        arcname = os.path.relpath(
                            file_path,
                            project_path,
                        )

                        printStatus(
                            "pack",
                            f"Packing {arcname}",
                            "info",
                        )

                        tar.add(
                            file_path,
                            arcname=arcname,
                        )

            printStatus(
                "done",
                f"Build complete in {archive}",
                "success",
            )

            if not os.path.isfile(archive):
                raise RuntimeError(
                    "Build did not produce an archive."
                )

            # ---------------------------------------------------------
            # Local registry
            # ---------------------------------------------------------

            if info["type"] == "local":

                local_root = localRegistryPath(
                    info["registry"]
                )

                # TODO: does local when it shouldn't
                
                release_dir = os.path.join(
                    local_root,
                    author,
                    distro,
                )

                os.makedirs(
                    release_dir,
                    exist_ok=True,
                )

                destination = os.path.join(
                    release_dir,
                    f"{version}.tar.gz",
                )

                if os.path.exists(destination):
                    raise RuntimeError(
                        f"Release {version} already exists."
                    )

                shutil.copy2(
                    archive,
                    destination,
                )

                return Result(
                    status="success",
                    success=True,
                    lines=[
                        (
                            f"Published "
                            f"{author}.{distro} "
                            f"release {version} "
                            f"to {release_dir}"
                        ),
                        (
                            f"Artifact: "
                            f"{os.path.basename(destination)}"
                        ),
                        (
                            f"Size: "
                            f"{os.path.getsize(destination)} bytes"
                        ),
                    ],
                    message=(
                        f"Published "
                        f"{author}.{distro} "
                        f"release {version} "
                        f"to {release_dir}"
                    ),
                    exit_code=0,
                )

            # ---------------------------------------------------------
            # Remote registry
            # ---------------------------------------------------------

            registry = info["registry"]

            base_url = registryBaseUrl(
                registry
            )

            url = (
                f"{base_url}/v1/"
                f"{urllib.parse.quote(author)}/"
                f"{urllib.parse.quote(distro)}/"
                f"{urllib.parse.quote(version)}"
            )

            boundary = (
                "----HydrogenPublish"
                + os.urandom(16).hex()
            )

            filename = os.path.basename(
                archive
            )

            with open(
                archive,
                "rb",
            ) as file:
                file_data = file.read()

            body = bytearray()

            body.extend(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; '
                    f'name="artifact"; '
                    f'filename="{filename}"\r\n'
                    f"Content-Type: application/gzip\r\n"
                    f"\r\n"
                ).encode()
            )

            body.extend(
                file_data
            )

            body.extend(
                (
                    f"\r\n"
                    f"--{boundary}--\r\n"
                ).encode()
            )

            request = urllib.request.Request(
                url,
                data=bytes(body),
                method="POST",
                headers={
                    "Content-Type": (
                        "multipart/form-data; "
                        f"boundary={boundary}"
                    ),
                    "Content-Length": str(
                        len(body)
                    ),
                },
            )

            printStatus(
                "send",
                (
                    f"Publishing "
                    f"{author}.{distro} "
                    f"release {version} "
                    f"to {registry}..."
                ),
                "info",
            )

            with urllib.request.urlopen(
                request
            ) as response:

                response_data = json.load(
                    response
                )

            artifact_name = response_data.get(
                "name",
                filename,
            )

            artifact_size = response_data.get(
                "size",
                os.path.getsize(archive),
            )

            artifact_sha256 = response_data.get(
                "sha256",
                "",
            )

            return Result(
                status="success",
                success=True,
                lines=[
                    (
                        f"Published "
                        f"{author}.{distro} "
                        f"release {version} "
                        f"to {registry}"
                    ),
                    (
                        f"Artifact: "
                        f"{artifact_name}"
                    ),
                    (
                        f"Size: "
                        f"{artifact_size} bytes"
                    ),
                    (
                        f"SHA-256: "
                        f"{artifact_sha256}"
                    ),
                ],
                message=(
                    f"Published "
                    f"{author}.{distro} "
                    f"release {version} "
                    f"to {registry}"
                ),
                exit_code=0,
            )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
            )

    except urllib.error.HTTPError as exc:

        try:
            detail = exc.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            detail = str(exc)

        return Result(
            status="error",
            success=False,
            lines=[
                (
                    f"Registry returned "
                    f"HTTP {exc.code}: {detail}"
                )
            ],
            message=(
                f"Registry returned "
                f"HTTP {exc.code}: {detail}"
            ),
            exit_code=1,
        )

    except urllib.error.URLError as exc:

        return Result(
            status="error",
            success=False,
            lines=[
                f"Could not reach registry: {exc}"
            ],
            message=(
                f"Could not reach registry: {exc}"
            ),
            exit_code=1,
        )

    except Exception as exc:

        return Result(
            status="error",
            success=False,
            lines=[
                f"Failed to publish {address}: {exc}"
            ],
            message=(
                f"Failed to publish {address}: {exc}"
            ),
            exit_code=1,
        )

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
        case "registry":
            if len(sys.argv) != 3 or not sys.argv[2].strip():
                printStatus("help", f"Usage: {COMMAND} registry <registry>", "warning")
                sys.exit(1)
            registry_value: str = sys.argv[2].strip()
            try:
                config_data: dict = {}
                if os.path.isfile(CONFIG_PATH):
                    with open(CONFIG_PATH) as config_file:
                        config_data = json.load(config_file)
                config_data["registry"] = registry_value
                with open(CONFIG_PATH, "w") as config_file:
                    json.dump(config_data, config_file, indent=4)
                    config_file.write("\n")
                printStatus("done", f"Home registry set to '{registry_value}'.", "success")
            except (OSError, ValueError) as exc:
                printStatus("fail", f"Could not save registry configuration: {exc}", "error")
                sys.exit(1)
        case "get":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} get <address>", "warning")
                sys.exit(1)
            address: str = sys.argv[2]
            result: Result = await installAsync(address)
            if not result.exit_code:
                await installSubdependencies(address)
        case "url":
            if len(sys.argv) != 3:
                printStatus("help", f"Usage: {COMMAND} url <address>", "warning")
                sys.exit(1)
            address: str = sys.argv[2]
            try:
                print(findDistroLocation(address))
            except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
                printDistroLocationError(address, exc)
                sys.exit(1)
        case "fetch":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} fetch <address>", "warning")
                sys.exit(1)
            address: str = sys.argv[2]
            temp_dir: str = tempfile.mkdtemp(prefix="hydrogen-fetch-")
            work_dir: str = os.path.join(temp_dir, "work")
            dist_dir: str = os.path.join(temp_dir, "dist")
            result: Result = await installAsync(address, emit=False, install_root=dist_dir, work_dir=work_dir)
            if not result.exit_code:
                await installSubdependencies(address, emit=False)
            print(os.path.join(os.path.abspath(dist_dir), getAddressInfo(address)["distro"]))
        case "view":
            if len(sys.argv) != 3:
                printStatus("help", f"Usage: {COMMAND} view <address>", "warning")
                sys.exit(1)
            result = viewDistro(sys.argv[2])
            printResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        case "getlib":
            if len(sys.argv) < 4:
                printStatus("help", f"Usage: {COMMAND} getlib <project> <address>", "warning")
                sys.exit(1)
            project: str = sys.argv[2]
            address = sys.argv[3]
            install_root: str = os.path.join(project, "libraries", getAddressInfo(address)['author'])
            result = await queueInstallToRoot(address, True, install_root, True)
            printResult(result)
            if result.exit_code:
                raise SystemExit(result.exit_code)
        case "publish":
            if len(sys.argv) < 4:
                printStatus("help", f"Usage: {COMMAND} publish <project_directory> <address>", "warning")
                sys.exit(1)
            result = await publishDistro(sys.argv[2],sys.argv[3])
            printResult(result)

            if result.exit_code:
                raise SystemExit(result.exit_code)
        case "rm":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {COMMAND} rm <address>", "warning")
                sys.exit(1)
            pub: str = sys.argv[2]
            printStatus("rm", f"Deleting {pub}", "info")
            if pub.strip() == "all":
                if os.path.exists("distrobase"):
                    shutil.rmtree("distrobase")
                else:
                    printStatus("info", "No address installed.", "muted")
            else:
                deleted: int = removeAddressVersions("distrobase", pub)
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
        case "getinternal":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {NAME} getinternal <address>", "warning")
                sys.exit(1)
            address = sys.argv[2]
            result = await installAsync(address, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
            if not result.exit_code:
                await installSubdependencies(address, install_root=INTERNAL_WW_DIR, work_dir=INTERNAL_TEMP_DIR)
        case "rminternal":
            if len(sys.argv) == 2:
                printStatus("help", f"Usage: {NAME} rminternal <address>", "warning")
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
                            if os.path.exists("distrobase"):
                                shutil.rmtree("distrobase")
                            return
                    except Exception:
                        for line in traceback.format_exc().split("\n"):
                            if line.strip():
                                print(cli(f"  {line}", CLI_ERROR))
            printStatus("miss", f"Unknown command: {sys.argv[1]}", "warning")
            print(f"Run {cli(f'{COMMAND} help', CLI_INFO)} for a list of commands.")
            
def entrypoint() -> None:
    asyncio.run(main())
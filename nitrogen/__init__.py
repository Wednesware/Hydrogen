import sys, zipfile, shutil, os, urllib.error, subprocess, traceback, tarfile, asyncio
from dataclasses import dataclass
from urllib.request import urlretrieve


VERSION: str = "26.40"
CLI_RESET: str = "\033[0m"
CLI_BOLD: str = "\033[1m"
CLI_DIM: str = "\033[90m"
CLI_INFO: str = "\033[94m"
CLI_SUCCESS: str = "\033[92m"
CLI_WARNING: str = "\033[93m"
CLI_ERROR: str = "\033[91m"

PUBLICATION_CACHE: dict[str, str] = {
    "n": "nitrogen",
    "mg": "magnesium",
    "he": "helium",
    "na": "sodium",
    "kr": "krypton",
    "o": "oxygen",
    "li": "lithium",
    "h": "hydrogen",
    "i": "iodine",
    "in": "indium",
    "ne": "neon",
    "c": "carbon",
    "b": "boron",
    "f": "fluorine",
    "s": "sulfur",
    "p": "phosphorus",
    "cl": "chlorine",
    "ar": "argon",
    "k": "potassium",
    "ca": "calcium",
    "sc": "scandium",
    "ti": "titanium",
    "v": "vanadium",
    "cr": "chromium",
    "mn": "manganese",
    "fe": "iron",
    "co": "cobalt",
    "ni": "nickel",
    "cu": "copper",
    "zn": "zinc",
    "ga": "gallium",
    "ge": "germanium",
    "as": "arsenic",
    "se": "selenium",
    "br": "bromine",
    "rb": "rubidium",
    "sr": "strontium",
    "y": "yttrium",
    "zr": "zirconium",
    "nb": "niobium",
    "mo": "molybdenum",
    "tc": "technetium",
    "ru": "ruthenium",
    "rh": "rhodium",
    "pd": "palladium"
}
REVERSE_PUBLICATION_CACHE: dict[str, str] = {v: k for k, v in PUBLICATION_CACHE.items()}
EXTENSIONS_DIR: str = os.path.join(os.path.dirname(__file__), "extensions")
TRUSTED_EXTENSIONS_FILE: str = os.path.join(os.path.dirname(__file__), ".TRUSTED_EXTENSIONS")
LEN_PATH: str = os.path.join(os.path.dirname(__file__), "ww", "len")

running_installs: dict[tuple[str, str], asyncio.Task] = {}


@dataclass(slots=True)
class InstallResult:
    status: str
    lines: list[str]
    exit_code: int = 0


def _cli(text: str, color: str = "", bold: bool = False) -> str:
    prefix: str = f"{CLI_BOLD if bold else ''}{color}"
    return f"{prefix}{text}{CLI_RESET if prefix else ''}"


def _print_status(label: str, message: str, tone: str = "info") -> None:
    palette: dict[str, str] = {
        "info": CLI_INFO,
        "success": CLI_SUCCESS,
        "warning": CLI_WARNING,
        "error": CLI_ERROR,
        "muted": CLI_DIM,
    }
    color: str = palette.get(tone, "")
    print(f"{_cli(f'[{label}]', color, bold=True)} {message}")


def _print_section(title: str) -> None:
    print(_cli(title, CLI_BOLD))


def _print_command(signature: str, description: str) -> None:
    print(f"  {_cli(signature, CLI_INFO)} {_cli('-', CLI_DIM)} {description}")


def _print_help() -> None:
    print(_cli(f"Nitrogen v{VERSION}", CLI_INFO, bold=True))
    print(_cli("Quick installer for Wednesware publications", CLI_DIM))
    print()
    _print_section("Usage")
    print("  n2 <command> [args]")
    print()
    _print_section("General")
    _print_command("get <publication> [release]", "Download a Wednesware publication from GitHub.")
    _print_command("rm <publication> [release]", "Delete one release or all installed releases for a publication.")
    _print_command("getdep [path]", "Install missing dependencies from a .nitrodep file, including nested ones.")
    _print_command("forcegetdep [path]", "Install all dependencies, regardless of whether they are already installed from a .nitrodep file, including nested ones, forcing reinstallation of all dependencies.")
    _print_command("build <format> [source] [output]", "Build the current Nitrogen project into a distributable format.")
    print()
    _print_section("Documentation")
    _print_command("readme [extension]", "Show the README for Nitrogen or an installed extension.")
    _print_command("license [extension]", "Show the license for Nitrogen or an installed extension.")
    _print_command("help", "Show this help message.")
    print()
    _print_section("Extensions")
    _print_command("list-ext", "List installed extensions and their local paths.")
    _print_command("trust-ext <extension>", "Trust an extension so it can run without confirmation.")
    _print_command("untrust-ext <extension>", "Remove trust for an extension.")
    _print_command("install-ext <extension>", "Install an extension from LEN.")
    _print_command("uninstall-ext <extension>", "Remove an installed extension.")
    _print_command("list-len", "List available extensions in LEN.")
    _print_command("load-len", "Clone the LEN repository locally.")
    _print_command("unload-len", "Remove the local LEN checkout.")


def _print_installed_extensions() -> None:
    _print_section("Installed extensions")
    sent: bool = False
    for ext_filename in [item for item in os.listdir(EXTENSIONS_DIR) if item.endswith(".n2x")]:
        print(f"  {_cli(ext_filename, CLI_INFO)} {_cli('->', CLI_DIM)} {os.path.join(EXTENSIONS_DIR, ext_filename)}")
        sent = True
    if not sent:
        _print_status("empty", "No extensions were detected.", "warning")


def _print_len_extensions() -> None:
    _print_section("Available extensions")
    printed: bool = False
    for ext_filename in [item for item in os.listdir(LEN_PATH) if item.endswith(".n2x")]:
        print(f"  {_cli(ext_filename, CLI_INFO)} {_cli('->', CLI_DIM)} https://github.com/Wednesware/LEN/blob/main/{ext_filename}")
        printed = True
    if not printed:
        _print_status("empty", "No extensions were detected in the LEN repository.", "warning")


def _print_extension_commands() -> None:
    _print_section("Custom commands")
    printed: bool = False
    for ext_path in [item for item in os.listdir(EXTENSIONS_DIR) if item.endswith(".n2x")]:
        print(f"  {_cli(ext_path.removesuffix('.n2x'), CLI_INFO)} {_cli('-', CLI_DIM)} Provided by '{ext_path}' at '{os.path.join(EXTENSIONS_DIR, ext_path)}'")
        printed = True
    if not printed:
        print(f"  {_cli('(none installed)', CLI_DIM)}")

def parsepub(pub: str) -> str:
    if pub.lower() in PUBLICATION_CACHE:
        return PUBLICATION_CACHE[pub.lower()]
    return pub


def _publication_dirname(pub: str, rel: str) -> str:
    pub_key: str = REVERSE_PUBLICATION_CACHE.get(pub.lower(), pub.lower())
    if rel == "latest":
        return f"ww/{pub_key}"
    return f"ww/{pub_key}{rel.replace('.', '_').replace('-', '_')}"


def _release_token(rel: str) -> str:
    return rel.replace(".", "_").replace("-", "_")


def _dependency_file_path(path: str) -> str:
    if path.endswith(".nitrodep"):
        return path
    return os.path.join(path, ".nitrodep")


def _print_install_result(result: InstallResult, color: bool = True) -> None:
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
    for line in result.lines:
        if prefix:
            print(f"{_cli(f'[{label}]', prefix, bold=True)} {line}")
        else:
            print(f"[{label}] {line}")


def _install_publication(pub: str, rel: str, reinstall: bool = True) -> InstallResult:
    pub = parsepub(pub)
    pub_lower: str = pub.lower()
    dirname: str = _publication_dirname(pub, rel)
    release_token: str = _release_token(rel)
    archive_path: str = f"{pub_lower}-{release_token}.zip"
    extract_dir: str = f"{pub_lower}-repo-{release_token}"

    try:
        if os.path.exists(dirname) and not reinstall:
            return InstallResult("info", [f"{pub_lower} {rel}: Publication is already installed."])

        try:
            urlretrieve(
                f"https://github.com/Wednesware/{pub.capitalize()}/releases/{rel + '/download' if rel == 'latest' else 'download/' + rel}/{pub_lower}.zip",
                archive_path,
            )
        except urllib.error.HTTPError:
            return InstallResult(
                "error",
                [f"{pub_lower} {rel}: Could not find this release. Are you sure you spelled it right?"],
                1,
            )

        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        if not os.path.exists("ww"):
            os.mkdir("ww")
        if os.path.exists(dirname):
            shutil.rmtree(dirname)

        source_root: str = next(os.scandir(extract_dir)).name
        shutil.move(os.path.join(extract_dir, source_root, pub_lower), dirname)
        return InstallResult("success", [f"{pub_lower} {rel}: Installation complete!"])
    except Exception:
        return InstallResult(
            "error",
            [line for line in traceback.format_exc().split("\n") if line.strip()],
            1,
        )
    finally:
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        if os.path.exists(archive_path):
            os.remove(archive_path)


def _queue_install(pub: str, rel: str, reinstall: bool = True) -> asyncio.Task:
    resolved_pub: str = parsepub(pub)
    key: tuple[str, str] = (resolved_pub.lower(), rel)
    if key in running_installs:
        _print_status("wait", f"Already queued {resolved_pub.lower()} {rel}", "muted")
        return running_installs[key]

    _print_status("queue", f"{resolved_pub.lower()} {rel}", "info")
    task: asyncio.Task = asyncio.create_task(asyncio.to_thread(_install_publication, resolved_pub, rel, reinstall))
    running_installs[key] = task

    def cleanup(completed_task: asyncio.Task, install_key: tuple[str, str] = key) -> None:
        if running_installs.get(install_key) is completed_task:
            running_installs.pop(install_key, None)

    task.add_done_callback(cleanup)
    return task


async def install_async(pub: str, rel: str, reinstall: bool = True, color: bool = True, emit: bool = True, fatal: bool = True) -> InstallResult:
    result: InstallResult = await _queue_install(pub, rel, reinstall)
    if emit:
        _print_install_result(result, color)
    if fatal and result.exit_code:
        raise SystemExit(result.exit_code)
    return result


async def _getdep_recursive(path: str, color: bool = True, log: bool = True, visited: set[str] | None = None, installed: set[tuple[str, str]] | None = None, force: bool = False) -> None:
    dep_path: str = _dependency_file_path(path)
    if visited is None:
        visited = set()
    if installed is None:
        installed = set()
    resolved_path: str = os.path.realpath(dep_path)
    if resolved_path in visited:
        return
    visited.add(resolved_path)

    if not os.path.isfile(dep_path):
        _print_status("miss", f"No dependency file found at '{dep_path}'", "warning")
        return
    with open(dep_path) as file:
        content: str = file.read()
    if not content.strip():
        if log:
            _print_status("done", "No dependencies needed.", "success")
        return

    deps: list[tuple[str, str]] = [(line.split()[0].strip(), line.split()[1].strip() if len(line.split()) > 1 else "latest") for line in content.split("\n") if line.strip()]
    if log:
        _print_status("deps", f"Loaded {len(deps)} dependenc{'y' if len(deps) == 1 else 'ies'} from {dep_path}", "info")
    pending_deps: list[tuple[str, str]] = []
    for pub, rel in deps:
        dep_key: tuple[str, str] = (parsepub(pub).lower(), rel)
        if dep_key in installed:
            continue
        installed.add(dep_key)
        pending_deps.append((pub, rel))

    tasks: list[asyncio.Task] = [_queue_install(pub, rel, (rel == "latest") or force) for pub, rel in pending_deps]
    results: list[InstallResult] = await asyncio.gather(*tasks)
    for result in results:
        _print_install_result(result, color)

    failures: int = sum(1 for result in results if result.exit_code)
    if failures:
        if log:
            _print_status("fail", f"Dependency install finished with {failures} failure(s).", "error")
        raise SystemExit(1)

    for pub, rel in deps:
        installed_dep_path: str = _dependency_file_path(_publication_dirname(parsepub(pub), rel))
        await _getdep_recursive(installed_dep_path, color=color, log=False, visited=visited, installed=installed)

    if log:
        _print_status("done", "All dependencies are ready.", "success")
                
async def getdep(path: str, color: bool = True, log: bool = True, force: bool = False) -> None:
    await _getdep_recursive(path, color=color, log=log, force=force)


async def _install_subdependencies(pub: str, rel: str, color: bool = True) -> None:
    resolved_pub: str = parsepub(pub)
    dep_path: str = _dependency_file_path(_publication_dirname(resolved_pub, rel))
    _print_status("deps", f"Checking sub-dependencies for {resolved_pub.lower()} {rel}", "info")
    if not os.path.isfile(dep_path):
        _print_status("info", "No sub-dependencies declared.", "muted")
        return
    await getdep(dep_path, color=color, log=True)
        
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
            
def load_len() -> None:
    try:
        if os.path.exists(LEN_PATH):
            unload_len()
        _print_status("sync", "Loading LEN from GitHub...", "info")
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
            print(_cli(f"  {line.rstrip()}", CLI_DIM))
        if proc.returncode != 0 and proc.returncode is not None:
            raise subprocess.CalledProcessError(proc.returncode, proc.args)
        proc.wait()
        _print_status("done", "LEN loaded successfully.", "success")
    except subprocess.CalledProcessError:
        _print_status("fail", "Could not load LEN from GitHub. Are you sure you have an internet connection?", "error")
        sys.exit(1)
        
def unload_len() -> None:
    if os.path.exists(LEN_PATH):
        shutil.rmtree(LEN_PATH)
        _print_status("done", "LEN unloaded.", "success")
    else:
        _print_status("info", "LEN is not loaded.", "muted")

async def build(format: str, source_path: str = ".", output_path: str = "build.%") -> None:
    _print_status("build", "Preparing build...", "info")
    try:
        output_path = output_path.replace("%", {
            "zip": "zip",
            "targz": "tar.gz",
            "n2x": "n2x",
            "py": "py"
        }[format])
    except KeyError:
        _print_status("fail", f"Unknown build format '{format}'.", "error")
        return
    if not os.path.isdir(source_path):
        _print_status("fail", f"Source path '{source_path}' does not exist or is not a directory.", "error")
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
            _print_status("build", f"Building project into {output_path}...", "info")
            with zipfile.ZipFile(output_abs, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_abs):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if should_skip(file_path):
                            continue
                        arcname = os.path.relpath(file_path, source_abs)
                        print(f"  {_cli('pack', CLI_DIM)} {arcname}")
                        zipf.write(file_path, arcname)
            _print_status("done", f"Build complete in {output_path}", "success")
        case "targz":
            _print_status("build", f"Building project into {output_path}...", "info")
            with tarfile.open(output_abs, "w:gz") as tar:
                for root, dirs, files in os.walk(source_abs):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if should_skip(file_path):
                            continue
                        arcname = os.path.relpath(file_path, source_abs)
                        print(f"  {_cli('pack', CLI_DIM)} {arcname}")
                        tar.add(file_path, arcname=arcname)
            _print_status("done", f"Build complete in {output_path}", "success")
        case "n2x":
            _print_status("build", f"Building project into {output_path}...", "info")
            required_files = ["ext.py", "README.md", "LICENSE.md", ".nitrodep"]
            with tarfile.open(output_abs, "w:gz") as tar:
                for file in required_files:
                    file_path = os.path.join(source_abs, file)
                    print(f"  {_cli('pack', CLI_DIM)} {file}")
                    if not os.path.isfile(file_path):
                        _print_status("fail", f"Required file for build not found: '{file}'", "error")
                        return
                    tar.add(file_path, arcname=file)
            _print_status("done", f"Build complete in {output_path}", "success")
        case "py":
            _print_status("deps", "Installing build dependencies...", "info")
            await asyncio.gather(
                install_async("magnesium", "26.11", False),
                install_async("iodine", "26.2", False),
            )
            from ww.i26_2 import run # type: ignore
            from ww.i26_2.widgets.text_input import TextInput # type: ignore
            with open(output_path, "w") as file:
                file.write(f"""
from setuptools import setup, find_packages
                           
setup(
    name="{run(TextInput('Project name: ', placeholder='myproject'))}",
    version="{run(TextInput('Project version: ', placeholder='26.1'))}",
    py_modules=[],
    entry_points={{
        "console_scripts": [
            "{run(TextInput('Command: ', placeholder='myprjct=myproject.cli:main'))}",
        ],
    }},
    author="{run(TextInput('Author name: ', placeholder='Your Name'))}",
    author_email="{run(TextInput('Author email: ', placeholder='you@email.com'))}",
    description="{run(TextInput('Short, one-line description: ', placeholder='...'))}",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="{run(TextInput('Project URL (example: GitHub page): ', placeholder='https://myproject.com'))}",
    packages=find_packages(),
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    license="MIT"
)              
""".strip())
            shutil.rmtree("ww/i26_2")
        case _:
            _print_status("fail", f"Unknown build format '{format}'.", "error")

async def main() -> None:
    if len(sys.argv) == 1:
        print(_cli(f"Nitrogen v{VERSION}", CLI_INFO, bold=True))
        print(_cli("Quick installer for Wednesware publications", CLI_DIM))
        print()
        print("Usage: n2 <command> [args]")
        print(f"Run {_cli('n2 help', CLI_INFO)} for a full command list.")
        sys.exit(0)

    if not os.path.exists(EXTENSIONS_DIR):
        os.makedirs(EXTENSIONS_DIR)
    if not os.path.exists(TRUSTED_EXTENSIONS_FILE):
        with open(TRUSTED_EXTENSIONS_FILE, "w") as file:
            file.write("")
    
    match sys.argv[1]:
        case "get":
            if len(sys.argv) == 2:
                _print_status("help", "Usage: n2 get <publication> [release]", "warning")
                sys.exit(1)
            pub: str = sys.argv[2]
            rel: str = sys.argv[3] if len(sys.argv) > 3 else "latest"
            result: InstallResult = await install_async(pub, rel)
            if not result.exit_code:
                await _install_subdependencies(pub, rel)
        case "rm":
            if len(sys.argv) == 2:
                _print_status("help", "Usage: n2 rm <publication> [release]", "warning")
                sys.exit(1)
            pub: str = parsepub(sys.argv[2])
            _print_status("rm", f"Deleting {pub}", "info")
            if pub.strip() == "all":
                if os.path.exists("ww"):
                    shutil.rmtree("ww")
                else:
                    _print_status("info", "No publications installed.", "muted")
            elif pub in PUBLICATION_CACHE or pub in REVERSE_PUBLICATION_CACHE:
                if len(sys.argv) > 3:
                    rel: str = sys.argv[3]
                    dirname: str = f"ww/{pub.lower()}{rel.replace('.', '_').replace('-', '_')}"
                    altdirname: str = f"ww/{REVERSE_PUBLICATION_CACHE[pub.lower()]}{rel.replace('.', '_').replace('-', '_')}"
                    deleted: int = 0
                    if os.path.exists(dirname):
                        shutil.rmtree(dirname)
                        deleted += 1
                    if os.path.exists(altdirname):
                        shutil.rmtree(altdirname)
                        deleted += 1
                    if deleted:
                        _print_status("done", "Operation complete.", "success")
                    else:
                        _print_status("miss", f"Release '{rel}' of publication '{pub.capitalize()}' is not installed here. Are you sure you spelled it right?", "warning")
                else:
                    deleted: int = 0
                    for path in os.listdir("ww"):
                        if path.startswith(pub.lower()) or path.startswith(REVERSE_PUBLICATION_CACHE[pub.lower()]):
                            shutil.rmtree(os.path.join("ww", path))
                            deleted += 1
                    if deleted:
                        _print_status("done", "Operation complete.", "success")
                    else:
                        _print_status("miss", f"Publication '{pub.capitalize()}' is not installed here. Are you sure you spelled it right?", "warning")
            else:
                _print_status("miss", f"Could not find publication '{pub.capitalize()}'. Are you sure you spelled it right?", "warning")
        case "getdep":
            path: str = (sys.argv[2] if len(sys.argv) > 2 else ".").removesuffix(".nitrodep") + "/.nitrodep"
            await getdep(path)
        case "forcegetdep":
            path: str = (sys.argv[2] if len(sys.argv) > 2 else ".").removesuffix(".nitrodep") + "/.nitrodep"
            await getdep(path, force=True)
        case "build":
            if len(sys.argv) == 2:
                _print_status("help", "Usage: n2 build <format(zip|targz|n2x|py)> [source path] [output path]", "warning")
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
                _print_status("help", "Usage: n2 trust-ext <extension>", "warning")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x"
            ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
            ext_dir_path: str = ext_path.replace('.', '-')
            trust(ext_filename, ext_dir_path)
        case "untrust-ext":
            if len(sys.argv) == 2:
                _print_status("help", "Usage: n2 untrust-ext <extension>", "warning")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x"
            with open(TRUSTED_EXTENSIONS_FILE, "w") as file:
                content: str = file.read()    
            file.write("\n".join([line for line in content.split("\n") if line.strip() != ext_filename]))
        case "list-ext":
            _print_installed_extensions()
        case "load-len":
            load_len()
        case "unload-len":
            unload_len()
        case "install-ext":
            if len(sys.argv) == 2:
                _print_status("help", "Usage: n2 install-ext <extension>", "warning")
                sys.exit(1)
            load_len()
            if os.path.exists(os.path.join(LEN_PATH, sys.argv[2] + ".n2x" if not sys.argv[2].endswith(".n2x") else sys.argv[2])):
                shutil.copy(os.path.join(LEN_PATH, sys.argv[2] + ".n2x"), EXTENSIONS_DIR)
                _print_status("done", f"Extension '{sys.argv[2]}' installed successfully.", "success")
            else:
                _print_status("miss", f"Extension '{sys.argv[2]}' not found in the LEN repository.", "warning")
        case "uninstall-ext":
            if len(sys.argv) == 2:
                _print_status("help", "Usage: n2 uninstall-ext <extension>", "warning")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x" if not sys.argv[2].endswith(".n2x") else sys.argv[2]
            ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
            if os.path.exists(ext_path):
                os.remove(ext_path)
                _print_status("done", f"Extension '{sys.argv[2]}' uninstalled successfully.", "success")
            else:
                _print_status("miss", f"Extension '{sys.argv[2]}' not installed.", "warning")
        case "list-len":
            load_len()
            _print_len_extensions()
        case "help":
            _print_help()
            print()
            _print_extension_commands()
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
                            nitrodep_path: str = os.path.join(ext_dir_path, ".nitrodep")
                            if os.path.exists(nitrodep_path):
                                print("\033[94m", end="", flush=True)
                                await getdep(nitrodep_path, log=False)
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
                                print(_cli(f"  {line}", CLI_ERROR))
            _print_status("miss", f"Unknown command: {sys.argv[1]}", "warning")
            print(f"Run {_cli('n2 help', CLI_INFO)} for a list of commands.")
            
def entrypoint() -> None:
    asyncio.run(main())
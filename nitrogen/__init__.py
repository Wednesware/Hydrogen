import sys, zipfile, shutil, os, urllib.error, subprocess, traceback
from urllib.request import urlretrieve


VERSION: str = "26.30"
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
    "in": "indium"
}
REVERSE_PUBLICATION_CACHE: dict[str, str] = {v: k for k, v in PUBLICATION_CACHE.items()}
EXTENSIONS_DIR: str = os.path.join(os.path.dirname(__file__), "extensions")
TRUSTED_EXTENSIONS_FILE: str = os.path.join(os.path.dirname(__file__), ".TRUSTED_EXTENSIONS")
OWNER_PATH: str = os.path.join(os.path.dirname(__file__), "ww", "owner")

def parsepub(pub: str) -> str:
    if pub.lower() in PUBLICATION_CACHE:
        return PUBLICATION_CACHE[pub.lower()]
    return pub

def install(pub: str, rel: str, do_getdep: str, reinstall: bool = True, color: bool = True) -> None:
    pub = parsepub(pub)
    print(f"Now installing: {pub.lower()}-{rel}")
    try:
        try:
            urlretrieve(f"https://github.com/Wednesware/{pub.capitalize()}/releases/{rel + '/download' if rel == 'latest' else 'download/' + rel}/{pub.lower()}.zip", f"{pub.lower()}.zip")
        except urllib.error.HTTPError:
            print(f"{'\033[91m' if color else ''}  Could not find release '{rel}' for publication '{pub.capitalize()}'. Are you sure you spelled it right?{'\033[0m' if color else ''}")
            sys.exit(1)
        with zipfile.ZipFile(f"{pub.lower()}.zip", "r") as zip_ref:
            zip_ref.extractall(f"{pub.lower()}-repo")
        dirname: str = f"ww/{REVERSE_PUBLICATION_CACHE[pub.lower()]}{rel.replace('.', '_').replace('-', '_')}" if rel != "latest" else f"ww/{REVERSE_PUBLICATION_CACHE[pub.lower()]}"
        if os.path.exists(dirname) and not reinstall:
            print(f"{'\033[94m' if color else ''}  Publication '{pub.capitalize()}' is already installed.{'\033[0m' if color else ''}")
        else:
            if not os.path.exists("ww"):
                os.mkdir("ww")
            if os.path.exists(dirname):
                shutil.rmtree(dirname)
            shutil.move(f"{pub.lower()}-repo/{next(os.scandir(f'{pub.lower()}-repo')).name}/{pub.lower()}", dirname)
            shutil.rmtree(f"{pub.lower()}-repo")
            os.remove(f"{pub.lower()}.zip")
            print(f"{'\033[92m' if color else ''}  Installation complete!{'\033[0m' if color else ''}")
            try:
                if do_getdep in ["y", "yes", "yeah", "true", "t"] or (do_getdep == "ask" and pub.lower() not in ["magnesium", "nitrogen"] and input(f"{'\033[94m' if color else ''}  Run 'getdep' on this new installation to get sub-dependencies? (Y/n) {'\033[0m' if color else ''}").strip().lower() in ["y", "yes", "yeah", "true", "t", ""]):
                    print(f"{'\033[94m' if color else ''}  Installing sub-dependencies...{'\033[0m' if color else ''}")
                    output: subprocess.CompletedProcess = subprocess.run(["python", __file__, "getdep", dirname], capture_output=True)
                    for line in output.stdout.decode().split("\n"):
                        print(f"  {line}")
                    for line in output.stderr.decode().split("\n"):
                        if line.strip():
                            print(f"{'\033[91m' if color else ''}  {line}{'\033[0m' if color else ''}")
            except (KeyboardInterrupt, EOFError):
                print()
                exit(0)
    except Exception:
        for line in traceback.format_exc().split("\n"):
            if line.strip():
                print(f"\033[91m  {line}\033[0m")
                
def getdep(path: str, reinstall: bool = True, color: bool = True) -> None:
    if not os.path.isfile(path):
        print(f"No dependency file found at '{path}'")
        sys.exit(0)
    with open(path) as file:
        content: str = file.read()
    if not content.strip():
        print(f"{'\033[92m' if color else ''}No dependencies needed!{'\033[0m' if color else ''}")
        sys.exit(0)
    else:
        deps: list[tuple[str, str]] = [(line.split()[0].strip(), line.split()[1].strip() if len(line.split()) > 1 else "latest") for line in content.split("\n") if line.strip()]
    print(f"Dependencies loaded: {len(deps)} ! {deps}")
    for dep in deps:
        install(*dep, do_getdep="yes", reinstall=reinstall)
        
def trust(ext_filename: str, ext_dir_path: str) -> None:
    ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
    if not os.path.exists(ext_path):
        print(f"\033[91mExtension '{ext_filename}' not found and cannot be trusted.")
        return
    with open(TRUSTED_EXTENSIONS_FILE) as file:
        content: str = file.read()
    if ext_filename not in content:
        try:
            if input(f"\033[38;5;208m/!\\ WARNING: You are running this extension for the first time.\n    Make sure to review the contents of\n      \033[0;1;3m{ext_dir_path}\033[0;38;5;208m\n    before running.\n    Trust extension and run command? (y/N) \033[0m").strip().lower() in ["y", "yes", "yeah", "true", "t", ""]:
                with open(TRUSTED_EXTENSIONS_FILE, "a") as file:
                    file.write(f"{ext_filename}\n")
            else:
                raise KeyboardInterrupt
        except (KeyboardInterrupt, EOFError):
            print("\n\033[91m    Extension not trusted. Aborting.\033[0m")
            sys.exit(0)
            
def load_owner() -> None:
    try:
        if os.path.exists(OWNER_PATH):
            unload_owner()
        print("\033[94mLoading OWNER from GitHub...\033[0m")
        proc = subprocess.Popen(
            [
                "git",
                "clone",
                "--progress",
                "https://github.com/Wednesware/OWNER.git",
                OWNER_PATH,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in proc.stdout:
            print(f"\033[90m  {line.rstrip()}\033[0m")
        if proc.returncode != 0 and proc.returncode is not None:
            raise subprocess.CalledProcessError(proc.returncode, proc.args)
        proc.wait()
        print("\033[92m  OWNER loaded successfully.\033[0m")
    except subprocess.CalledProcessError:
        print("\033[91m  Could not load OWNER from GitHub. Are you sure you have an internet connection?\033[0m")
        sys.exit(1)
        
def unload_owner() -> None:
    if os.path.exists(OWNER_PATH):
        shutil.rmtree(OWNER_PATH)
        print("\033[92mOWNER unloaded.\033[0m")
    else:
        print("OWNER is not loaded.\033[0m")

def main() -> None:
    if len(sys.argv) == 1:
        print(f"Nitrogen (wwn/n2) by Wednesware v{VERSION}")
        print("Usage: n2 <command> [args]")
        print("Use 'n2 help' for a list of commands.")
        sys.exit(0)

    match sys.argv[1]:
        case "get":
            if len(sys.argv) == 2:
                print("Usage: n2 get <publication> [release (latest by default)]")
                sys.exit(1)
            install(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "latest", sys.argv[4] if len(sys.argv) > 4 else "ask")
        case "rm":
            if len(sys.argv) == 2:
                print("Usage: n2 rm <publication> [release (latest by default)]")
                sys.exit(1)
            pub: str = parsepub(sys.argv[2])
            print(f"Now deleting: {pub}")
            if pub.strip() == "all":
                if os.path.exists("ww"):
                    shutil.rmtree("ww")
                else:
                    print("  No publications installed.")
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
                        print("\033[92m  Operation complete.")
                    else:
                        print(f"  Release '{rel}' of publication '{pub.capitalize()}' is not installed here. Are you sure you spelled it right?")
                else:
                    deleted: int = 0
                    for path in os.listdir("ww"):
                        if path.startswith(pub.lower()) or path.startswith(REVERSE_PUBLICATION_CACHE[pub.lower()]):
                            shutil.rmtree(os.path.join("ww", path))
                            deleted += 1
                    if deleted:
                        print("\033[92m  Operation complete.")
                    else:
                        print(f"  Publication '{pub.capitalize()}' is not installed here. Are you sure you spelled it right?")
            else:
                print(f"  Could not find publication '{pub.capitalize()}'. Are you sure you spelled it right?")
        case "getdep":
            path: str = sys.argv[2] if len(sys.argv) > 2 else ".nitrodep"
            getdep(path)
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
                print("Usage: n2 trust <extension>")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x"
            ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
            ext_dir_path: str = ext_path.replace('.', '-')
            trust(ext_filename, ext_dir_path)
        case "untrust-ext":
            if len(sys.argv) == 2:
                print("Usage: n2 untrust <extension>")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x"
            with open(TRUSTED_EXTENSIONS_FILE, "w") as file:
                content: str = file.read()    
            file.write("\n".join([line for line in content.split("\n") if line.strip() != ext_filename]))
        case "list-ext":
            print("Available extensions:")
            sent: bool = False
            for ext_filename in [item for item in os.listdir(EXTENSIONS_DIR) if item.endswith(".n2x")]:
                print(f"  {ext_filename} - {os.path.join(EXTENSIONS_DIR, ext_filename)}")
                sent = True
            if not sent:
                print("\033[91m  No extensions were detected.\033[0m")
        case "load-owner":
            load_owner()
        case "unload-owner":
            unload_owner()
        case "install-ext":
            if len(sys.argv) == 2:
                print("Usage: n2 install-ext <extension>")
                sys.exit(1)
            load_owner()
            if os.path.exists(os.path.join(OWNER_PATH, sys.argv[2] + ".n2x" if not sys.argv[2].endswith(".n2x") else sys.argv[2])):
                shutil.copy(os.path.join(OWNER_PATH, sys.argv[2] + ".n2x"), EXTENSIONS_DIR)
                print(f"\033[92m  Extension '{sys.argv[2]}' installed successfully.\033[0m")
        case "uninstall-ext":
            if len(sys.argv) == 2:
                print("Usage: n2 uninstall-ext <extension>")
                sys.exit(1)
            ext_filename: str = sys.argv[2] + ".n2x" if not sys.argv[2].endswith(".n2x") else sys.argv[2]
            ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
            if os.path.exists(ext_path):
                os.remove(ext_path)
                print(f"\033[92m  Extension '{sys.argv[2]}' uninstalled successfully.\033[0m")
        case "list-owner":
            load_owner()
            for ext_filename in [item for item in os.listdir(OWNER_PATH) if item.endswith(".n2x")]:
                print(f"  {ext_filename} - https://github.com")
        case "help":
            print("Usage: n2 <command> [args]")
            print("General commands:")
            print("  get <publication> [release (latest by default)] [get subdependencies? (y/n)] - Download a Wednesware publication from GitHub")
            print("  rm <publication> [release (all by default)] - Delete all releases or a specific release of a publication from the current directory.")
            print("  getdep [path] - Smart-install all dependencies from a .nitrodep file")
            print("Documentation/info commands:")
            print("  readme [extension] - Show the README file of an extension. If no extension is specified, show the README of Nitrogen itself.")
            print("  license [extension] - Show the license of an extension. If no extension is specified, show the license of Nitrogen itself.")
            print("  list-ext - List all installed extensions and their paths.")
            print("  help - Show this help message")
            print("Extension management commands:")
            print("  trust-ext <extension> - Trust an extension so that it can be run without confirmation. Only use this for extensions you have reviewed and trust.")
            print("  untrust-ext <extension> - Untrust an extension so that it will require confirmation before running.")
            print("  pack-n2x <ext.py> [.nitrodep] [README.md] [LICENSE.md] - Pack an extension into a .n2x Nitrogen extension file for distribution. The .nitrodep, README.md, and LICENSE.md files are optional but recommended.")
            print("OWNER-based commands:")
            print("  load-owner - Load the OWNER repository from GitHub. Other OWNER-based commands will do this automatically.")
            print("  unload-owner - Unload the OWNER repository from the current directory.")
            print("  install-ext <extension> - Download select verified extensions from the Official Wednesware Nitrogen Extension Repository (OWNER)")
            print("  uninstall-ext <extension> - Uninstall an extension.")
            print("Custom commands (via extensions):")
            for ext_path in [item for item in os.listdir(EXTENSIONS_DIR) if item.endswith(".n2x")]:
                print(f"  {ext_path.removesuffix('.n2x')} - Provided by the extension '{ext_path}' at '{os.path.join(EXTENSIONS_DIR, ext_path)}'")
        case _:
            for ext_filename2 in [item for item in os.listdir(EXTENSIONS_DIR) if item.endswith(".n2x") or item.endswith(".n2xp")]:
                ext_path2: str = os.path.join(EXTENSIONS_DIR, ext_filename2)
                for ext_filename in [item for item in os.listdir(ext_path2) if item.endswith(".n2x")] if ext_filename.endswith(".n2xp") else [ext_filename2]:
                    try:
                        if sys.argv[1] == ext_filename.removesuffix(".n2x"):
                            ext_path: str = os.path.join(EXTENSIONS_DIR, ext_filename)
                            ext_dir_path: str = ext_path.replace('.', '-')
                            with zipfile.ZipFile(ext_path, "r") as zip_ref:
                                zip_ref.extractall(ext_dir_path)
                            trust(ext_filename, ext_dir_path)
                            script_path: str = os.path.join(ext_dir_path, "ext.py")
                            nitrodep_path: str = os.path.join(ext_dir_path, ".nitrodep")
                            if os.path.exists(nitrodep_path):
                                print("\033[94m", end="", flush=True)
                                getdep(nitrodep_path, reinstall=False, color=False)
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
                                print(f"\033[91m  {line}\033[0m")
            print(f"Unknown command: {sys.argv[1]}")
            print("Use 'n2 help' for a list of commands.")

if __name__ == "__main__":
    main()

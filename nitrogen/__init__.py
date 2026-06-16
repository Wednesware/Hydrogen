import sys, zipfile, shutil, os, urllib.error, subprocess, traceback
from urllib.request import urlretrieve


PUBLICATION_CACHE: dict[str, str] = {
    "n": "nitrogen",
    "mg": "magnesium",
    "he": "helium",
    "li": "lithium",
    "o": "oxygen"
}

REVERSE_PUBLICATION_CACHE: dict[str, str] = {v: k for k, v in PUBLICATION_CACHE.items()}

def parsepub(pub: str) -> str:
    if pub.lower() in PUBLICATION_CACHE:
        return PUBLICATION_CACHE[pub.lower()]
    return pub

def install(pub: str, rel: str, getdep: str) -> None:
    pub = parsepub(pub)
    print(f"Now installing: {pub.lower()}-{rel}")
    try:
        try:
            urlretrieve(f"https://github.com/Wednesware/{pub.capitalize()}/releases/{rel + '/download' if rel == 'latest' else 'download/' + rel}/{pub.lower()}.zip", f"{pub.lower()}.zip")
        except urllib.error.HTTPError:
            print(f"Error: Could not find release '{rel}' for publication '{pub.capitalize()}'. Are you sure you spelled it right?")
            sys.exit(1)
        with zipfile.ZipFile(f"{pub.lower()}.zip", "r") as zip_ref:
            zip_ref.extractall(f"{pub.lower()}-repo")
        dirname: str = f"{pub.lower()}{rel.replace('.', '_').replace('-', '_')}" if rel != "latest" else pub.lower()
        altdirname: str = f"{REVERSE_PUBLICATION_CACHE[pub.lower()]}{rel.replace('.', '_').replace('-', '_')}" if rel != "latest" else REVERSE_PUBLICATION_CACHE[pub.lower()]
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
        if os.path.exists(altdirname):
            shutil.rmtree(altdirname)
        shutil.move(f"{pub.lower()}-repo/{next(os.scandir(f'{pub.lower()}-repo')).name}/{pub.lower()}", dirname)
        shutil.rmtree(f"{pub.lower()}-repo")
        shutil.copytree(dirname, altdirname)
        os.remove(f"{pub.lower()}.zip")
        print(f"\033[92m  Installation complete!\033[0m")
        try:
            if getdep == "yes" or (getdep == "ask" and pub.lower() not in ["magnesium", "nitrogen"] and input(f"\033[94m  Run 'getdep' on this new installation to get sub-dependencies? (Y/n) \033[0m").strip().lower() in ["y", "yes", "yeah", "true", "t", ""]):
                print("\033[94m  Installing sub-dependencies...\033[0m")
                output: subprocess.CompletedProcess = subprocess.run(["python", __file__, "getdep", dirname], capture_output=True)
                for line in output.stdout.decode().split("\n"):
                    print(f"  {line}")
                for line in output.stderr.decode().split("\n"):
                    if line.strip():
                        print(f"\033[91m  {line}\033[0m")
        except (KeyboardInterrupt, EOFError):
            print()
            exit(0)
    except Exception:
        for line in traceback.format_exc().split("\n"):
            if line.strip():
                print(f"\033[91m  {line}\033[0m")

def main() -> None:
    if len(sys.argv) == 1:
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
            if len(sys.argv) > 3:
                rel: str = sys.argv[3]
                dirname: str = f"{pub.lower()}{rel.replace('.', '_').replace('-', '_')}"
                altdirname: str = f"{REVERSE_PUBLICATION_CACHE[pub.lower()]}{rel.replace('.', '_').replace('-', '_')}"
                if os.path.exists(dirname):
                    shutil.rmtree(dirname)
                if os.path.exists(altdirname):
                    shutil.rmtree(altdirname)
            else:
                for path in os.listdir():
                    if path.startswith(pub.lower()) or path.startswith(REVERSE_PUBLICATION_CACHE[pub.lower()]):
                        shutil.rmtree(path)
        case "getdep":
            nitrodep_path: str = os.path.join(sys.argv[2] if len(sys.argv) > 2 else "", ".nitrodep")
            if not os.path.isfile(nitrodep_path):
                print(f"No dependency file found at '{nitrodep_path}'")
                sys.exit(0)
            with open(nitrodep_path) as file:
                content: str = file.read()
            if not content.strip():
                print("\033[92mNo dependencies needed!\033[0m")
                sys.exit(0)
            else:
                deps: list[tuple[str, str]] = [(line.split()[0].strip(), line.split()[1].strip() if len(line.split()) > 1 else "latest") for line in content.split("\n") if line.strip()]
            print(f"Dependencies loaded: {len(deps)} ! {deps}")
            for dep in deps:
                install(*dep, getdep="yes")
        case "readme":
            with open(os.path.join(os.path.dirname(__file__), "README.md")) as file:
                print(file.read())
        case "help":
            print("Usage: n2 <command> [args]")
            print("Commands:")
            print("  get <publication> [release (latest by default)] [get subdependencies? (y/n)] - Download a Wednesware publication from GitHub")
            print("  rm <publication> [release (all by default)] - Delete all releases or a specific release of a publication from the current directory.")
            print("  getdep [path] - Smart-install all dependencies from a .nitrodep file")
            print("  readme - Show the README file")
            print("  help - Show this help message")
        case _:
            print(f"Unknown command: {sys.argv[1]}")
            print("Use 'n2 help' for a list of commands.")
            
if __name__ == "__main__":
    main()

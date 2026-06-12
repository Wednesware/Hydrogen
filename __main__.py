import sys, zipfile, shutil, os, urllib.error, subprocess
from urllib.request import urlretrieve

if len(sys.argv) == 1:
    print("Usage: python nitrogen <command> [args]")
    print("Use 'python nitrogen help' for a list of commands.")
    sys.exit(0)

def install(pub: str, rel: str, getdep: str) -> None:
    print(f"Now installing: {pub.lower()}-{rel}")
    try:
        urlretrieve(f"https://github.com/Wednesware/{pub.capitalize()}/releases/{rel + '/download' if rel == 'latest' else 'download/' + rel}/{pub.lower()}.zip", f"{pub.lower()}.zip")
    except urllib.error.HTTPError:
        print(f"Error: Could not find release '{rel}' for publication '{pub.capitalize()}'. Are you sure you spelled it right?")
        sys.exit(1)
    with zipfile.ZipFile(f"{pub.lower()}.zip", "r") as zip_ref:
        zip_ref.extractall(f"{pub.lower()}-repo")
    if os.path.exists(f"{pub.lower()}"):
        shutil.rmtree(f"{pub.lower()}")
    shutil.move(f"{pub.lower()}-repo/{next(os.scandir(f'{pub.lower()}-repo')).name}/{pub.lower()}", f"{pub.lower()}")
    shutil.rmtree(f"{pub.lower()}-repo")
    os.remove(f"{pub.lower()}.zip")
    print(f"\033[92m  Installation complete!\033[0m")
    try:
        if getdep == "yes" or (getdep == "ask" and input(f"\033[94m  Run 'getdep' on this new installation to get sub-dependencies? (Y/n) \033[0m").strip().lower() in ["y", "yes", "yeah", "true", "t", ""]):
            print("\033[94m  Installing sub-dependencies...")
            output: str = subprocess.run(["python", __file__, "getdep", pub], capture_output=True)
            for line in output.stdout.decode().split("\n"):
                print(f"  {line}")
    except (KeyboardInterrupt, EOFError):
        print()
        exit(0)

match sys.argv[1]:
    case "get":
        if len(sys.argv) == 2:
            print("Usage: python nitrogen get <publication> [release (latest by default)]")
        install(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "latest", sys.argv[4] if len(sys.argv) > 4 else "ask")
        print("Run 'rm -rf nitrogen' to remove this installer.")
    case "getdep":
        nitrodep_path: str = os.path.join(sys.argv[2] if len(sys.argv) > 2 else "", ".nitrodep")
        if not os.path.isfile(nitrodep_path):
            print(f"\033[92mNo dependencies needed or no dependency file found at '{nitrodep_path}'\033[0m")
            sys.exit(0)
        with open(nitrodep_path) as file:
            content: str = file.read()
        if not content.strip():
            print("\033[92mNo dependencies needed!\033[0m")
            sys.exit(0)
        else:
            deps: list[tuple[str, str]] = [(line.split()[0].strip(), line.split()[1].strip() if len(line.split()) > 1 else "latest") for line in content.split("\n")]
        print(f"Dependencies loaded: {len(deps)} ! {deps}")
        for dep in deps:
            install(*dep, getdep="yes")
    case "readme":
        with open(os.path.join(os.path.dirname(__file__), "README.md")) as file:
            print(file.read())
    case "help":
        print("Usage: python nitrogen <command> [args]")
        print("Commands:")
        print("  get <publication> [release (latest by default)] [get subdependencies? (y/n)] - Download a Wednesware publication from GitHub")
        print("  getdep [path] - Smart-install all dependencies from a .nitrodep file.")
        print("  readme - Show the README file")
        print("  help - Show this help message")
    case _:
        print(f"Unknown command: {sys.argv[1]}")
        print("Use 'python nitrogen help' for a list of commands.")

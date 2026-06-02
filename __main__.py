import sys, zipfile, shutil, os, urllib.error
from urllib.request import urlretrieve

if len(sys.argv) == 1:
    print("Usage: python Nitrogen <command> [args]")
    print("Use 'python Nitrogen help' for a list of commands.")
    sys.exit(0)

match sys.argv[1]:
    case "get":
        if len(sys.argv) == 2:
            print("Usage: python Nitrogen get <publication> [release (latest by default)]")
        try:
            urlretrieve(f"https://github.com/Wednesware/{sys.argv[2].capitalize()}/releases/{sys.argv[3] if len(sys.argv) > 3 else 'latest'}/download/{sys.argv[2].lower()}.zip", f"{sys.argv[2].lower()}.zip")
        except urllib.error.HTTPError:
            print(f"Error: Could not find release '{sys.argv[3] if len(sys.argv) > 3 else 'latest'}' for publication '{sys.argv[2].capitalize()}'. Are you sure you spelled it right?")
            sys.exit(1)
        with zipfile.ZipFile(f"{sys.argv[2].lower()}.zip", "r") as zip_ref:
            zip_ref.extractall(f"{sys.argv[2].lower()}-repo")
        shutil.move(f"{sys.argv[2].lower()}-repo/{next(os.scandir(f'{sys.argv[2].lower()}-repo')).name}/{sys.argv[2].lower()}", f"{sys.argv[2].lower()}")
        shutil.rmtree(f"{sys.argv[2].lower()}-repo")
        os.remove(f"{sys.argv[2].lower()}.zip")
        print("\033[92mInstallation complete! Run 'rm -rf Nitrogen' to remove this installer.\033[0m")
    case "readme":
        with open(os.path.join(os.path.dirname(__file__), "README.md")) as file:
            print(file.read())
    case "help":
        print("Usage: python Nitrogen <command> [args]")
        print("Commands:")
        print("  get <publication> [release (latest by default)] - Download a Wednesware publication from GitHub")
        print("  readme - Show the README file")
        print("  help - Show this help message")
    case _:
        print(f"Unknown command: {sys.argv[1]}")
        print("Use 'python Nitrogen help' for a list of commands.")
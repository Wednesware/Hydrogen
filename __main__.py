import sys, zipfile, shutil, os, subprocess
from urllib.request import urlretrieve

match sys.argv[1]:
    case "get":
        if len(sys.argv) == 2:
            print("Usage: python nitrogen get <publication> [release (latest by default)]")
        urlretrieve(f"https://github.com/Wednesware/{sys.argv[2].capitalize()}/releases/{sys.argv[3] if len(sys.argv) > 3 else 'latest'}/download/{sys.argv[2].lower()}.zip", f"{sys.argv[2].lower()}.zip")
        with zipfile.ZipFile(f"{sys.argv[2].lower()}.zip", "r") as zip_ref:
            zip_ref.extractall(f"{sys.argv[2].lower()}-repo")
        shutil.move(f"{sys.argv[2].lower()}-repo/{sys.argv[2].lower()}", f"{sys.argv[2].lower()}")
        shutil.rmtree(f"{sys.argv[2].lower()}-repo")
        os.remove(f"{sys.argv[2].lower()}.zip")
        while True:
            print("Download complete. Delete Nitrogen? (y/n)")
            choice = input("> ").lower()
            if choice == "y":
                while True:
                    print("Add 'getnitrogen' command to reinstall Nitrogen whenever without taking up space? (y/n)")
                    choice2 = input("> ").lower()
                    if choice2 == "y":
                        if shutil.which("git") is None:
                            print("Error: Git is not installed or not in PATH.")
                            sys.exit(1)

                        try:
                            subprocess.run(
                                ["git", "clone", "https://github.com/Wednesware/Nitrogen.git"],
                                check=True
                            )
                            print("Nitrogen downloaded successfully. Run 'python nitrogen help' for usage instructions.")
                        except subprocess.CalledProcessError as e:
                            print(f"Git clone failed with exit code {e.returncode}")
                            sys.exit(e.returncode)
                        break
                    elif choice2 == "n":
                        break
                shutil.rmtree(f"{sys.argv[2].lower()}")
                break
            elif choice == "n":
                break
    case "readme":
        with open(os.path.join(os.path.dirname(__file__), "README.md")) as file:
            print(file.read())
    case "help":
        print("Usage: python nitrogen <command> [args]")
        print("Commands:")
        print("  get <publication> [release (latest by default)] - Download a Wednesware publication from GitHub")
        print("  readme - Show the README file")
        print("  help - Show this help message")
    case _:
        print(f"Unknown command: {sys.argv[1]}")
        print("Use 'python nitrogen help' for a list of commands.")
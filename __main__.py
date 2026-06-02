import sys, zipfile, shutil, os, pathlib, platform, stat
from urllib.request import urlretrieve

if len(sys.argv) == 1:
    print("Usage: python Nitrogen <command> [args]")
    print("Use 'python Nitrogen help' for a list of commands.")
    sys.exit(0)

match sys.argv[1]:
    case "get":
        if len(sys.argv) == 2:
            print("Usage: python Nitrogen get <publication> [release (latest by default)]")
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
                        nitrogen_repo_url: str = "https://github.com/Wednesware/Nitrogen.git"
                        def install_linux():
                            bin_dir = pathlib.Path.home() / ".local" / "bin"
                            bin_dir.mkdir(parents=True, exist_ok=True)

                            script_path = bin_dir / "getnitrogen"

                            script_content = f"#!/bin/sh\ngit clone {nitrogen_repo_url}"
                            script_path.write_text(script_content)
                            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

                            print(f"Installed to {script_path}")
                            print("Make sure ~/.local/bin is in your PATH")

                        def install_windows():
                            bin_dir = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Programs" / "getnitrogen"
                            bin_dir.mkdir(parents=True, exist_ok=True)

                            script_path = bin_dir / "getnitrogen.cmd"

                            script_content = f"git clone {nitrogen_repo_url}"

                            script_path.write_text(script_content)

                            print(f"Installed to {script_path}")
                            print("Add this folder to PATH if not already:")
                            print(str(bin_dir))
                        system = platform.system().lower()

                        if system == "linux":
                            install_linux()
                            print("\nDone. You can now run: getnitrogen")
                        elif system == "windows":
                            install_windows()
                            print("\nDone. You can now run: getnitrogen")
                        else:
                            print(f"Unsupported OS: {system}")
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
        print("Usage: python Nitrogen <command> [args]")
        print("Commands:")
        print("  get <publication> [release (latest by default)] - Download a Wednesware publication from GitHub")
        print("  readme - Show the README file")
        print("  help - Show this help message")
    case _:
        print(f"Unknown command: {sys.argv[1]}")
        print("Use 'python Nitrogen help' for a list of commands.")
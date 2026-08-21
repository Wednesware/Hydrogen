# Wednesware Hydrogen

Sourcegen-based Distrobase installer.

## Installation methods:

### From PyPI via pipx (recommended, global install, run with `h2`):
* `pipx install wwh`

### From PyPI via pip (virtual environment or global install, run with `h2`):
* `pip install wwh`
* Note: You may need to create a virtual environment for this method first on some machines. [Learn how to do this here.](https://docs.python.org/3/library/venv.html)

### From GitHub via Nitrogen (local install, run with `python -m ww.h`):
* `n2 get hydrogen`

### From GitHub via terminal (local install, run with `python -m hydrogen`):
* `git clone https://github.com/Wednesware/Hydrogen.git hydrogen`

### From Github via browser (local install, run with `python -m hydrogen`):
* [Click here to install the latest Hydrogen release as a zip file](https://github.com/Wednesware/Hydrogen/releases/latest/download/hydrogen.zip) [or click here to browse releases](https://github.com/Wednesware/Hydrogen/releases).
* Unpack using `bsdtar -xf hydrogen.zip`

## Upgrade methods:

### From PyPI via pipx
* `pipx upgrade wwh`

### From PyPI via pip
* `pip install wwh --upgrade`

## Usage:

### Commands

* `h2 get <address>` - Download a distribution from an address.
* `h2 view <address>` - View information about a distribution.
* `h2 url <address>` - Get the URL of a tar.gz artifact via an address.
* `h2 fetch <address>` - Download a distribution to a temporary directory and print the extracted path.
* `h2 getlib <project> <address>` - Download a distribution into '<project>/libraries/author'.
* `h2 publish <project> <address>` - Publish a distribution from a project directory to a registry.
* `h2 rm <address>` - Delete one distribution or all installed distributions.
* `h2 getdep [path]` - Install missing dependencies from a .hydrodep file, including nested ones.
* `h2 forcegetdep [path]` - Install all dependencies, regardless of whether they are already installed from a .hydrodep file, including nested ones, forcing reinstallation of all dependencies.
* `h2 updlibs <project>` - Reinstall all distributions in '<project>/libraries' from their exact installed addresses.
* `h2 registry <registry>` - Set your home registry which will be used in operations when a registry is not specified.
* `h2 stage get <address>` - Stage a dependency install into ./ww.
* `h2 stage getlib <project> <address>` - Stage a library install into ./<project>/libraries/author.
* `h2 stage adddep <address>` - Stage adding one dependency line to ./.hydrodep.
* `h2 stage rmdep <address>` - Stage removing one dependency line from ./.hydrodep.
* `h2 stage getdep [target]` - Stage running getdep at ./<target>.
* `h2 stage forcegetdep [target]` - Stage running forcegetdep at ./<target>.
* `h2 stage updlibs [target]` - Stage running updlibs at ./<target>.
* `h2 stage rm <address>` - Stage dependency removal from ./ww.
* `h2 stage rmlib <project> <address>` - Stage library removal from ./<project>/libraries/author.
* `h2 stage publish <project> <address>` - Stage publishing a project distribution to a registry.
* `h2 stage registry <registry>` - Stage setting the home registry.
* `h2 stage cmd <command>` - Stage a shell command to run during stage execute/commit.
* `h2 stage getinternal <address>` - Stage a dependency install into hydrogen/ww.
* `h2 stage rminternal <address>` - Stage dependency removal from hydrogen/ww.
* `h2 stage getdepinternal [target]` - Stage running getdep against hydrogen/ww at ./<target>.
* `h2 stage cancel [subcommand|last] [args]` - Cancel one staged line, the last line, or the full stage.
* `h2 stage execute` - Execute staged actions in exact order. Slower but guarantees order of operations.
* `h2 stage commit` - Execute staged installs/removals in batched mode. Faster but does not guarantee order of operations.
* `h2 readme [extension]` - Show the README for Hydrogen or an installed extension.
* `h2 license [extension]` - Show the license for Hydrogen or an installed extension.
* `h2 help` - Show this help message.
* `h2 list-ext` - List installed extensions and their local paths.
* `h2 trust-ext <extension>` - Trust an extension so it can run without confirmation.
* `h2 untrust-ext <extension>` - Remove trust for an extension.
* `h2 install-ext <extension>` - Install an extension from LEN.
* `h2 uninstall-ext <extension>` - Remove an installed extension.
* `h2 list-len` - List available extensions in LEN.
* `h2 load-len` - Clone the LEN repository locally.
* `h2 unload-len` - Remove the local LEN checkout.

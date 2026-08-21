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

* `h2 get <publication> [release (latest by default)]` - Download a Wednesware publication from GitHub.
  * Example usage: `h2 get magnesium 26.3` (installs Magnesium release 26.3 to `ww/mg26_3`.)
  * Tip: you can use chemical symbols for publications. Example: `h2 get mg 26.3`
* `h2 url <address>` - Print the resolved distribution URL for an address without installing it.
* `h2 fetch <address>` - Download a distribution to a temporary directory and print the extracted path.
* `h2 getlib <project> <publication> [release (latest by default)]` - Download a Wednesware publication to `./<project>/libraries/ww`.
  * Example usage: `h2 getlib app magnesium 26.3` (installs to `./app/libraries/ww/mg26_3`.)
* `h2 rm <publication> [release (all by default)]` - Delete all releases or a specific release of a publication from the current directory.
  * Example usage: `h2 rm magnesium 26.3` (deletes `./ww/magnesium26_3` and `./ww/mg26_3` only if present)
  * Or: `h2 rm magnesium` (deletes all installed versions in `./ww` for both long and short publication names)
  * Tip: you can use chemical symbols here too.
* `h2 getdep [path]` - Search recursively under path for every `.nitrodep` and install dependencies.
* `h2 forcegetdep [path]` - Same as `getdep`, but force reinstall dependencies.
* `h2 updlibs <project>` - Reinstall all libraries found in `./<project>/libraries/ww` by reading installed publication names and versions.
* `h2 stage get <publication> [release]` - Stage a dependency install into `./ww`.
* `h2 stage getlib <project> <publication> [release]` - Stage a library install into `./<project>/libraries/ww`.
* `h2 stage adddep <publication> [release]` - Stage adding a dependency to `./.nitrodep`.
* `h2 stage rmdep <publication> [release]` - Stage removing a dependency from `./.nitrodep`.
* `h2 stage getdep [target]` - Stage running `getdep` at target path (`.` by default).
* `h2 stage forcegetdep [target]` - Stage running `forcegetdep` at target path (`.` by default).
* `h2 stage updlibs [target]` - Stage running `updlibs` at target path (`.` by default).
* `h2 stage rm <publication> [release]` - Stage removal from `./ww`.
* `h2 stage rmlib <project> <publication> [release]` - Stage removal from `./<project>/libraries/ww`.
* `h2 stage compat <publication> [release]` - Stage compatibility rewrite for Wednesware imports in a directory.
* `h2 stage cmd <*cmd>` - Stage a shell command.
* `h2 stage cancel [subcommand|last] [*arguments]` - Cancel staged entries, last entry, or all entries.
* `h2 stage execute` - Run staged actions in the order they were staged.
* `h2 stage commit` - Run staged actions in batched mode for faster installs.
* `h2 help` - Prints a formatted help message to the terminal.

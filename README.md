# Wednesware Nitrogen

Easy, ultra-lightweight installer for Wednesware publications.

This publication does not require [Wednesware Magnesium](https://wednesware.github.io/home#magnesium) to run.

## Installation methods:

### From PyPI (recommended, global install, run with `n2`):
* `pip install wwn`
* Note: You may need to create a virtual environment first on some machines. [Learn how to do this here.](https://docs.python.org/3/library/venv.html)

### From GitHub via terminal (local install, run with `python -m nitrogen.nitrogen`):
* `git clone https://github.com/Wednesware/Nitrogen.git nitrogen`

### From Github via browser (local install, run with `python -m nitrogen.nitrogen`):
* [Click here to install the latest Nitrogen release as a zip file](https://github.com/Wednesware/Nitrogen/releases/latest/download/nitrogen.zip)
* Unpack using `bsdtar -xf nitrogen.zip`

## Upgrade methods:

### From GitHub via Nitrogen (self-upgrade) (recommended, fastest, guaranteed upgrade)
* `n2 get n`

### From PyPI
* `pip install wwn --upgrade`

## Usage:

`n2 get <publication> [release (latest by default)] [get subdependencies? (y/n)]` - Download a Wednesware publication from GitHub.
* Example usage: `n2 get magnesium 26.3 n` (installs Magnesium version 26.3 without installing sub-dependencies)
* Tip: you can use the chemical symbol for all publications to get them faster. Example: `n2 get mg 26.3 n`
`n2 getdep [path]` - Smart-install all dependencies from a .nitrodep file.
* Example usage: `n2 getdep helium` (installs all dependencies required by Helium)
`n2 readme` - Prints the contents of the README.md file.
`n2 help` - Prints a formatted help message to the terminal.

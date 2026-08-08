# Wednesware Sourcegen

## Info

* Wednesware Sourcegen is a stripped-down fork of [Nitrogen](https://github.com/Wednesware/Nitrogen).
* Sourcegen is **not** meant to be used as a tool, but rather as a template for creating your own installer.

## Why Sourcegen

* Sourcegen is a direct fork of Nitrogen, which means it features LEN support, is completely dependency-free and open-source. Sourcegen modifies Nitrogen to let YOU customize the installation process or anything else as the code adapts to it.

## Perfect for

* Developers who want to create their own installer for their software.
* Developers who want to learn how Nitrogen works and how to modify it to their needs.
* Power-users who want to change up the command names of Nitrogen to their liking.

## How to start

### Template (recommended)

1. `gh repo create <your-repo-name> --template Wednesware/Sourcegen --public` (or `--private` for a private repository)
2. `gh repo clone <your-username>/<your-repo-name>`
3. done!

### Fork

1. `gh repo fork Wednesware/Sourcegen --clone`
2. done!

## Important note

* After creating a repository with Sourcegen as a template, open your IDE and press `CTRL+SHIFT+F` (or whatever your IDE's search tab bind is). Search for `# TODO` and one-by-one assess and modify the lines. `# TODO` marks lines that should be changed before the installer is distributed.
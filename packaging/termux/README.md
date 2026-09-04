# HOOK for Termux

This directory contains the recipe and repository bootstrap for installing HOOK with Termux's normal package manager.

After the HOOK Termux repository is configured, installation is simply:

```sh
pkg update
pkg install hook
```

The package installs the `hook` executable and the HOOK Python runtime. It depends on Termux's `python` package.

## Bootstrap the repository

Until the package is accepted into the official Termux repositories, users must add the HOOK package repository once. The repository is published by the `termux-repository.yml` GitHub Actions workflow.

```sh
bash packaging/termux/add-repo.sh
pkg update
pkg install hook
```

The package is intentionally named `hook`, so the command is exactly `hook` after installation.

## Official Termux repository

The long-term goal is upstreaming the package to the Termux package repositories. Once upstreamed, the custom repository bootstrap will no longer be necessary and `pkg install hook` will work directly after a normal `pkg update`.

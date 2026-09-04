#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

TERMUX_PKG_HOMEPAGE=https://github.com/Leila150/hook
TERMUX_PKG_DESCRIPTION="HOOK programming language and command-line tool"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="Leila150"
TERMUX_PKG_VERSION=1.1.1
TERMUX_PKG_SRCURL=https://github.com/Leila150/hook/archive/refs/tags/v${TERMUX_PKG_VERSION}.tar.gz
TERMUX_PKG_SHA256=SKIP_CHECKSUM
TERMUX_PKG_DEPENDS="python"
TERMUX_PKG_PLATFORM_INDEPENDENT=true

termux_step_make_install() {
    cd "$TERMUX_PKG_SRCDIR"

    # HOOK is distributed as a language/runtime, not as a Python distribution.
    # Install its source tree directly and provide a small native Termux launcher.
    rm -rf "$TERMUX_PREFIX/share/hook"
    mkdir -p "$TERMUX_PREFIX/share/hook" "$TERMUX_PREFIX/bin"
    cp -R src/hook/. "$TERMUX_PREFIX/share/hook/"
    install -m 0755 packaging/termux/hook "$TERMUX_PREFIX/bin/hook"
}

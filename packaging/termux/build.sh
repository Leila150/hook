#!/data/data/com.termux/files/usr/bin/bash

TERMUX_PKG_HOMEPAGE=https://github.com/Leila150/hook
TERMUX_PKG_DESCRIPTION="HOOK programming language and command-line tool"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="Leila150"
TERMUX_PKG_VERSION=1.0.0
TERMUX_PKG_SRCURL=https://github.com/Leila150/hook/archive/refs/tags/v${TERMUX_PKG_VERSION}.tar.gz
TERMUX_PKG_SHA256=SKIP
TERMUX_PKG_DEPENDS="python"
TERMUX_PKG_PLATFORM_INDEPENDENT=true

termux_step_make_install() {
    cd "$TERMUX_PKG_SRCDIR"
    python -m pip install . --no-build-isolation --prefix="$TERMUX_PREFIX" --root="$TERMUX_PKG_TMPDIR" --no-deps
}

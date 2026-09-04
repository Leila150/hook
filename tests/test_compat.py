from pathlib import Path

from hook.compat import CompatibilityConfig, WinlatorRuntime, host_arch


def test_host_arch_is_text():
    assert isinstance(host_arch(), str)
    assert host_arch()


def test_environment_sets_wine_prefix(tmp_path):
    runtime = WinlatorRuntime(CompatibilityConfig(wine_prefix=tmp_path / "prefix"))
    env = runtime.environment()
    assert env["WINEPREFIX"] == str(tmp_path / "prefix")
    assert (tmp_path / "prefix").exists()


def test_arm64_command_uses_box64_when_configured(monkeypatch):
    runtime = WinlatorRuntime(CompatibilityConfig(box64="/opt/box64", wine="/opt/wine"))
    monkeypatch.setattr("hook.compat.host_arch", lambda: "aarch64")
    assert runtime.command("game.exe", ["--test"]) == ["/opt/box64", "/opt/wine", "game.exe", "--test"]


def test_rootfs_wraps_command_with_proot(tmp_path, monkeypatch):
    runtime = WinlatorRuntime(CompatibilityConfig(
        rootfs=tmp_path,
        proot="/opt/proot",
        box64="/opt/box64",
        wine="/opt/wine",
    ))
    monkeypatch.setattr("hook.compat.host_arch", lambda: "aarch64")
    command = runtime.command("game.exe")
    assert command[:4] == ["/opt/proot", "-r", str(tmp_path), "--"]
    assert command[4:] == ["/opt/box64", "/opt/wine", "game.exe"]

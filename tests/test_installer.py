import sys
from portbin import installer, platform


def test_step_matches_platform():
    win_step = {"platform": ["win32"], "type": "download"}
    linux_step = {"platform": ["linux"], "type": "download"}
    all_step = {"type": "download"}

    assert installer.step_matches_platform(all_step) is True

    if sys.platform == "win32":
        assert installer.step_matches_platform(win_step) is True
        assert installer.step_matches_platform(linux_step) is False
    elif sys.platform.startswith("linux"):
        assert installer.step_matches_platform(win_step) is False
        assert installer.step_matches_platform(linux_step) is True


def test_shim_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(platform, "default_bin_dir", lambda: tmp_path)

    shim_step = {
        "type": "shim",
        "name": "mytool",
        "command": "mytool --arg",
        "bin": str(tmp_path),
    }

    installer._shim(shim_step, {})

    if platform.is_windows():
        shim_file = tmp_path / "mytool.cmd"
        assert shim_file.exists()
        assert "@echo off" in shim_file.read_text(encoding="utf-8")
    else:
        shim_file = tmp_path / "mytool"
        assert shim_file.exists()
        assert "#!/bin/sh" in shim_file.read_text(encoding="utf-8")
        assert (shim_file.stat().st_mode & 0o111) != 0

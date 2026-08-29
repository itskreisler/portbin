from __future__ import annotations

import os

from portbin.platform import is_windows


def _reg_key(scope: str):
    import winreg

    if scope == "machine":
        return winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    return winreg.HKEY_CURRENT_USER, r"Environment"


def _read_reg_path(scope: str) -> list[str]:
    import winreg

    try:
        key, sub = _reg_key(scope)
        with winreg.OpenKey(key, sub, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            value, _ = winreg.QueryValueEx(k, "Path")
    except FileNotFoundError:
        value = ""
    return [p for p in value.split(";") if p]


def _write_reg_path(scope: str, entries: list[str]) -> None:
    import winreg

    key, sub = _reg_key(scope)
    flags = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
    data = ";".join(entries)
    with winreg.CreateKeyEx(key, sub, 0, flags) as k:
        winreg.SetValueEx(k, "Path", 0, winreg.REG_EXPAND_SZ, data)


def _broadcast() -> None:
    try:
        import ctypes

        HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x001A, 0x0002
        message = ctypes.c_wchar_p("Environment")
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, message, SMTO_ABORTIFHUNG, 5000, None
        )
    except Exception:
        pass


def path_contains(value: str, scope: str = "machine") -> bool:
    entries = _read_reg_path(scope) if is_windows() else [p for p in os.environ.get("Path", "").split(";") if p]
    return value.rstrip("\\/").lower() in {e.rstrip("\\/").lower() for e in entries}


def add_path(value: str, scope: str = "machine") -> bool:
    if not is_windows():
        return _env_add_path(value)
    entries = _read_reg_path(scope)
    normalized = {e.rstrip("\\/").lower() for e in entries}
    if value.rstrip("\\/").lower() in normalized:
        return False
    entries.append(value)
    _write_reg_path(scope, entries)
    _broadcast()
    return True


def remove_path(value: str, scope: str = "machine") -> bool:
    if not is_windows():
        return _env_remove_path(value)
    entries = _read_reg_path(scope)
    target = value.rstrip("\\/").lower()
    kept = [e for e in entries if e.rstrip("\\/").lower() != target]
    if len(kept) == len(entries):
        return False
    _write_reg_path(scope, kept)
    _broadcast()
    return True


def set_var(name: str, value: str, scope: str = "machine") -> None:
    if not is_windows():
        os.environ[name] = value
        return
    import winreg

    key, sub = _reg_key(scope)
    flags = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
    with winreg.CreateKeyEx(key, sub, 0, flags) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_EXPAND_SZ, value)
    _broadcast()


def del_var(name: str) -> None:
    if not is_windows():
        os.environ.pop(name, None)
        return
    import winreg

    for scope in ("machine", "user"):
        try:
            key, sub = _reg_key(scope)
            with winreg.OpenKey(key, sub, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
                winreg.DeleteValue(k, name)
        except (FileNotFoundError, OSError):
            continue
    _broadcast()


def _env_add_path(value: str) -> bool:
    entries = [p for p in os.environ.get("Path", "").split(";") if p]
    normalized = {e.rstrip("\\/").lower() for e in entries}
    if value.rstrip("\\/").lower() in normalized:
        return False
    entries.append(value)
    os.environ["Path"] = ";".join(entries)
    return True


def _env_remove_path(value: str) -> bool:
    entries = os.environ.get("Path", "").split(";")
    target = value.rstrip("\\/").lower()
    kept = [e for e in entries if e and e.rstrip("\\/").lower() != target]
    changed = len(kept) != len(entries)
    os.environ["Path"] = ";".join(kept)
    return changed
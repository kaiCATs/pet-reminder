# ================================================================
# AUTOSTART
# Manages Windows registry entry for startup with Windows.
# Works correctly only in a compiled .exe build.
# ================================================================

import winreg

APP_NAME = "PetReminder"
_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def set_autostart(exe_path: str, enable: bool = True):
    """Add or remove the app from Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[autostart] set_autostart: {e}")


def is_autostart_enabled() -> bool:
    """Return True if the registry entry exists."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

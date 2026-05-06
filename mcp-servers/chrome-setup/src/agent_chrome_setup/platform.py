import platform as _platform
from pathlib import Path
import os

def get_platform() -> str:
    system = _platform.system()
    if system == "Darwin": return "darwin"
    elif system == "Windows": return "win32"
    return "linux"

def get_chrome_path() -> str | None:
    """Find Chrome executable. Returns path or None."""
    plat = get_platform()
    if plat == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif plat == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(local, r"Google\Chrome\Application\chrome.exe") if local else "",
        ]
    else:
        candidates = ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium-browser", "/usr/bin/chromium"]

    for c in candidates:
        if c and Path(c).exists():
            return c
    return None

def get_profile_path() -> Path:
    """Get the agent Chrome profile directory path."""
    if get_platform() == "win32":
        base = Path(os.environ.get("USERPROFILE", Path.home()))
    else:
        base = Path.home()
    return base / ".config" / "chrome-profiles" / "agent"

def get_shortcut_path() -> Path:
    """Get the desktop shortcut path."""
    if get_platform() == "darwin":
        return Path.home() / "Desktop" / "Agent Chrome.app"
    elif get_platform() == "win32":
        return Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop" / "Agent Chrome.lnk"
    else:
        return Path.home() / "Desktop" / "Agent Chrome.desktop"

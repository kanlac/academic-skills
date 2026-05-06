import os
import stat
import subprocess
import shutil
from pathlib import Path
from .platform import get_platform, get_chrome_path, get_profile_path, get_shortcut_path


def create_desktop_shortcut() -> dict:
    """Create a desktop shortcut to launch Chrome with CDP on port 9225."""
    plat = get_platform()
    chrome_path = get_chrome_path()
    if not chrome_path:
        return {"success": False, "error": "Chrome not found", "shortcut_path": "", "platform": plat, "chrome_path": ""}

    shortcut_path = get_shortcut_path()
    profile_path = get_profile_path()

    try:
        if plat == "darwin":
            _create_mac_app(shortcut_path, chrome_path, profile_path)
        elif plat == "win32":
            _create_win_lnk(shortcut_path, chrome_path, profile_path)
        else:
            _create_linux_desktop(shortcut_path, chrome_path, profile_path)
    except Exception as e:
        return {"success": False, "error": str(e), "shortcut_path": str(shortcut_path), "platform": plat, "chrome_path": chrome_path}

    return {
        "success": True,
        "shortcut_path": str(shortcut_path),
        "platform": plat,
        "chrome_path": chrome_path,
    }


def _create_mac_app(app_path: Path, chrome_path: str, profile_path: Path):
    """Create a macOS .app bundle."""
    contents = app_path / "Contents"
    macos_dir = contents / "MacOS"
    resources_dir = contents / "Resources"
    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    # Copy Chrome's icon if available
    chrome_icon = Path("/Applications/Google Chrome.app/Contents/Resources/app.icns")
    icon_entry = ""
    if chrome_icon.exists():
        shutil.copy2(chrome_icon, resources_dir / "app.icns")
        icon_entry = "    <key>CFBundleIconFile</key>\n    <string>app.icns</string>"

    # Info.plist
    plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.agent.chrome</string>
    <key>CFBundleName</key>
    <string>Agent Chrome</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
{icon_entry}
</dict>
</plist>'''
    (contents / "Info.plist").write_text(plist, encoding="utf-8")

    # Launcher script
    launcher = f'''#!/bin/bash
CHROME="{chrome_path}"
PROFILE="{profile_path}"
exec "$CHROME" \\
  --remote-debugging-port=9225 \\
  --user-data-dir="$PROFILE" \\
  --no-first-run \\
  --no-default-browser-check
'''
    launcher_path = macos_dir / "launcher"
    launcher_path.write_text(launcher, encoding="utf-8")
    launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Remove quarantine attribute so Gatekeeper doesn't block it
    subprocess.run(["xattr", "-cr", str(app_path)], capture_output=True)


def _create_win_lnk(lnk_path: Path, chrome_path: str, profile_path: Path):
    """Create a Windows .lnk shortcut via PowerShell."""
    # Use single quotes for paths in PowerShell to avoid escaping issues
    chrome_escaped = str(chrome_path).replace("'", "''")
    lnk_escaped = str(lnk_path).replace("'", "''")
    profile_str = str(profile_path)
    args = f'--remote-debugging-port=9225 --user-data-dir="{profile_str}" --no-first-run --no-default-browser-check'

    script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{lnk_escaped}')
$Shortcut.TargetPath = '{chrome_escaped}'
$Shortcut.Arguments = '{args}'
$Shortcut.Description = 'Agent Chrome (CDP port 9225)'
$Shortcut.Save()
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"PowerShell shortcut creation failed: {result.stderr.strip()}")


def _create_linux_desktop(desktop_path: Path, chrome_path: str, profile_path: Path):
    """Create a Linux .desktop file."""
    # Escape spaces in paths per Desktop Entry spec (backslash-escape)
    chrome_escaped = chrome_path.replace(" ", r"\ ")
    profile_escaped = str(profile_path).replace(" ", r"\ ")
    content = f"""[Desktop Entry]
Name=Agent Chrome
Exec={chrome_escaped} --remote-debugging-port=9225 --user-data-dir={profile_escaped} --no-first-run --no-default-browser-check
Type=Application
Icon=google-chrome
"""
    desktop_path.write_text(content, encoding="utf-8")
    desktop_path.chmod(desktop_path.stat().st_mode | stat.S_IXUSR)

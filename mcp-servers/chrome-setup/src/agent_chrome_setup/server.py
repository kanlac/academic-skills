import asyncio
from functools import partial
from mcp.server.fastmcp import FastMCP
from .port import check_cdp_port, open_new_tab, launch_chrome_process
from .profile import create_profile, customize_profile
from .shortcut import create_desktop_shortcut
from .platform import get_platform, get_chrome_path, get_profile_path, get_shortcut_path

mcp = FastMCP("agent-chrome-setup")


async def _run_sync(func, *args, **kwargs):
    """Run a blocking function in a thread to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


@mcp.tool()
async def check_port() -> dict:
    """Check if Chrome CDP is available on port 9225. Returns availability status, browser version, and WebSocket URL."""
    return await _run_sync(check_cdp_port)


@mcp.tool()
async def setup_profile(profile_name: str = "Agent", color: str = "teal") -> dict:
    """Create a dedicated Chrome profile directory. Color options: teal, purple, orange, green, red. Note: name/color are applied after Chrome's first launch via customize_profile."""
    return await _run_sync(create_profile, profile_name, color)


@mcp.tool()
async def apply_profile_theme(profile_name: str = "Agent", color: str = "teal") -> dict:
    """Apply name and color theme to the Chrome profile. Call AFTER Chrome has been launched at least once (it creates its own state files on first run)."""
    return await _run_sync(customize_profile, profile_name, color)


@mcp.tool()
async def create_shortcut() -> dict:
    """Create a desktop shortcut to launch Chrome with CDP debugging on port 9225."""
    return await _run_sync(create_desktop_shortcut)


@mcp.tool()
async def get_status() -> dict:
    """Get complete setup status: profile, shortcut, port, Chrome installation."""
    profile_path = get_profile_path()
    shortcut_path = get_shortcut_path()
    chrome_path = get_chrome_path()
    port_info = await _run_sync(check_cdp_port)

    profile_exists = profile_path.exists()
    shortcut_exists = shortcut_path.exists()
    chrome_found = chrome_path is not None
    port_available = port_info["available"]

    return {
        "profile_exists": profile_exists,
        "profile_path": str(profile_path),
        "shortcut_exists": shortcut_exists,
        "shortcut_path": str(shortcut_path),
        "port_available": port_available,
        "browser_version": port_info.get("browser_version"),
        "platform": get_platform(),
        "chrome_found": chrome_found,
        "chrome_path": chrome_path or "",
        "setup_complete": all([profile_exists, shortcut_exists, chrome_found, port_available]),
    }


@mcp.tool()
async def diagnose() -> dict:
    """Diagnose connection issues and provide fix suggestions."""
    issues = []
    chrome_path = get_chrome_path()
    profile_path = get_profile_path()
    port_info = await _run_sync(check_cdp_port)

    if not chrome_path:
        issues.append({
            "code": "chrome_not_found",
            "message": "未找到 Google Chrome",
            "fix": "请安装 Google Chrome: https://www.google.com/chrome/",
        })

    if not profile_path.exists():
        issues.append({
            "code": "profile_missing",
            "message": "Agent Chrome profile 不存在",
            "fix": "调用 setup_profile 工具创建 profile",
        })
    elif not (profile_path / "First Run").exists() and not (profile_path / "Local State").exists():
        issues.append({
            "code": "profile_corrupted",
            "message": "Profile 目录不完整",
            "fix": "调用 setup_profile 工具重新创建",
        })

    if not port_info["available"]:
        import subprocess as sp
        try:
            if get_platform() == "darwin":
                result = sp.run(["pgrep", "-f", "Google Chrome"], capture_output=True, text=True)
                chrome_running = result.returncode == 0
            elif get_platform() == "win32":
                result = sp.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], capture_output=True, text=True)
                chrome_running = "chrome.exe" in result.stdout
            else:
                result = sp.run(["pgrep", "-f", "chrome"], capture_output=True, text=True)
                chrome_running = result.returncode == 0
        except Exception:
            chrome_running = False

        if chrome_running:
            issues.append({
                "code": "chrome_no_debug_port",
                "message": "Chrome 正在运行但未启用调试端口",
                "fix": "请完全退出 Chrome（确保进程结束），然后使用桌面上的 'Agent Chrome' 快捷方式重新启动",
            })
        else:
            issues.append({
                "code": "chrome_not_running",
                "message": "Chrome 未运行",
                "fix": "请使用桌面上的 'Agent Chrome' 快捷方式启动 Chrome",
            })

    return {"issues": issues, "healthy": len(issues) == 0}


@mcp.tool()
async def launch_chrome() -> dict:
    """Launch Chrome with Agent profile on CDP port 9225. Waits until Chrome is responsive. If Chrome is already running on 9225, returns immediately. Requires: all other Chrome instances must be quit first."""
    return await _run_sync(launch_chrome_process)


@mcp.tool()
async def open_url(url: str) -> dict:
    """Open a URL in the Agent Chrome instance. Requires Chrome running on port 9225."""
    return await _run_sync(open_new_tab, url)


def main():
    mcp.run()

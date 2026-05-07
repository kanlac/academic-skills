import json
import subprocess
import time
import urllib.request
import urllib.error
from .platform import get_platform, get_chrome_path, get_profile_path

CDP_PORT = 9225


def _get_endpoints() -> list[str]:
    """Get CDP endpoints to try, with IPv6 fallback on macOS."""
    endpoints = [f"http://127.0.0.1:{CDP_PORT}"]
    if get_platform() == "darwin":
        endpoints.append(f"http://[::1]:{CDP_PORT}")
    return endpoints


def check_cdp_port() -> dict:
    """Check if Chrome CDP is available on port 9225."""
    for base in _get_endpoints():
        try:
            url = f"{base}/json/version"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                return {
                    "available": True,
                    "browser_version": data.get("Browser"),
                    "ws_url": data.get("webSocketDebuggerUrl"),
                    "error": None,
                }
        except (urllib.error.URLError, OSError):
            continue
        except Exception:
            continue

    return {
        "available": False,
        "browser_version": None,
        "ws_url": None,
        "error": "connection_refused",
    }


def open_new_tab(url: str) -> dict:
    """Open a URL in Chrome via CDP."""
    for base in _get_endpoints():
        try:
            target_url = f"{base}/json/new?{url}"
            req = urllib.request.Request(target_url, method="PUT")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return {
                    "success": True,
                    "tab_id": data.get("id", ""),
                    "url": data.get("url", url),
                }
        except Exception:
            continue

    return {"success": False, "tab_id": "", "url": url, "error": "Chrome not reachable on port 9225"}


def _clean_stale_locks(profile_path):
    """Remove stale Chrome lock files that prevent launch."""
    from pathlib import Path
    lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie"]
    for name in lock_files:
        lock = Path(profile_path) / name
        if lock.exists() or lock.is_symlink():
            try:
                lock.unlink()
            except OSError:
                pass


def launch_chrome_process() -> dict:
    """Launch user's own Chrome with CDP debugging port enabled."""
    status = check_cdp_port()
    if status["available"]:
        return {"success": True, "already_running": True, "browser_version": status["browser_version"]}

    chrome_path = get_chrome_path()
    if not chrome_path:
        return {"success": False, "error": "Chrome not found on this system"}

    profile_path = get_profile_path()
    _clean_stale_locks(profile_path)

    chrome_args = [
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={profile_path}",
        "--remote-allow-origins=*",
    ]

    try:
        if get_platform() == "darwin":
            subprocess.Popen(
                ["open", "-a", "Google Chrome", "--args"] + chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        elif get_platform() == "win32":
            subprocess.Popen(
                [chrome_path] + chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            subprocess.Popen(
                [chrome_path] + chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
    except Exception as e:
        return {"success": False, "error": f"Failed to launch Chrome: {e}"}

    for _ in range(30):
        time.sleep(0.5)
        status = check_cdp_port()
        if status["available"]:
            return {"success": True, "already_running": False, "browser_version": status["browser_version"]}

    return {"success": False, "error": "Chrome launched but CDP port not responding after 15 seconds"}

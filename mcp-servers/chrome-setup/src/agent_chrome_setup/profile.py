import json
from pathlib import Path
from .platform import get_profile_path

COLOR_MAP = {
    "teal": -16745597,
    "purple": -8708190,
    "orange": -1543926,
    "green": -15753896,
    "red": -2543579,
}


def create_profile(profile_name: str = "Agent", color: str = "teal") -> dict:
    """Create a dedicated Chrome profile directory.

    Only creates the directory and First Run sentinel. Chrome creates its own
    state files on first launch — pre-creating them causes crashes on Chrome 147+.
    Profile name/color are applied after first launch via customize_profile.
    """
    profile_path = get_profile_path()
    already_existed = profile_path.exists()

    profile_path.mkdir(parents=True, exist_ok=True)
    (profile_path / "First Run").touch()

    return {
        "success": True,
        "profile_path": str(profile_path),
        "profile_name": profile_name,
        "color": color,
        "already_existed": already_existed,
    }


def customize_profile(profile_name: str = "Agent", color: str = "teal") -> dict:
    """Apply name and color to an existing Chrome profile (call after first Chrome launch)."""
    profile_path = get_profile_path()
    local_state_path = profile_path / "Local State"

    if not local_state_path.exists():
        return {"success": False, "error": "Profile not initialized yet. Launch Chrome first."}

    color_seed = COLOR_MAP.get(color, COLOR_MAP["teal"])

    # Patch Local State
    local_state = json.loads(local_state_path.read_text(encoding="utf-8"))
    profile_section = local_state.setdefault("profile", {})
    info_cache = profile_section.setdefault("info_cache", {})
    default_info = info_cache.setdefault("Default", {})
    default_info.update({
        "name": profile_name,
        "is_using_default_name": False,
        "profile_highlight_color": color_seed,
        "profile_color_seed": color_seed,
    })
    local_state_path.write_text(json.dumps(local_state, indent=2), encoding="utf-8")

    # Patch Preferences
    prefs_path = profile_path / "Default" / "Preferences"
    if prefs_path.exists():
        prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
        prefs.setdefault("profile", {})["name"] = profile_name
        prefs.setdefault("browser", {}).setdefault("theme", {}).update({
            "user_color2": color_seed,
            "color_variant2": 0,
        })
        prefs_path.write_text(json.dumps(prefs, indent=2), encoding="utf-8")

    return {"success": True, "profile_name": profile_name, "color": color}

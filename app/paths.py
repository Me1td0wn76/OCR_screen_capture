"""Path helpers that work both in dev and as a PyInstaller-frozen exe."""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """Directory for writable, user-facing files (config.json, logs).

    - Frozen: the folder that contains the .exe (so the user can find/edit config).
    - Dev: the project root (parent of this package).
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Directory for bundled, read-only resources (OCR models, icon).

    - Frozen: PyInstaller unpacks data files into sys._MEIPASS.
    - Dev: the project root.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def bundled_models_dir() -> Path:
    """Read-only models shipped inside the build (offline fallback)."""
    return resource_dir() / "models"


def default_models_dir() -> Path:
    """Default, writable location where downloaded models are stored.

    Sits next to the exe (or project root in dev) so the user can find it.
    Overridable via config's ``model_dir``.
    """
    return app_dir() / "models"


def config_path() -> Path:
    return app_dir() / "config.json"


def web_dir() -> Path:
    """Directory of the Flask static assets / built SPA (bundled resource)."""
    return resource_dir() / "app" / "web"


"""Load/save user configuration (config.json) with sane defaults."""
from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

from .paths import config_path, default_models_dir

log = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    # --- Setup / language ---
    # ``language`` selects the recognition model; the model file + input height
    # are derived from app.models_registry. ``model_dir`` empty means "use the
    # default writable location next to the app" (resolved by resolve_model_dir).
    "setup_completed": False,
    "language": "japan",
    "model_dir": "",
    # --- OCR ---
    "ocr": {
        "text_score": 0.5,
    },
    # --- Behaviour ---
    "auto_ocr": True,            # watch the clipboard and OCR new images
    "copy_to_clipboard": True,   # put recognized text back on the clipboard
    "show_notifications": True,  # tray balloon with a result preview
    # --- Text to speech (offline, Windows SAPI5) ---
    "tts": {
        "speak_on_ocr": False,
        "voice_match": "Japanese",  # substring matched against voice name/id
        "rate": 175,                # words per minute-ish
        "volume": 1.0,
    },
    # --- Translation via a local OpenAI-compatible server (Ollama, LM Studio) ---
    "translate": {
        "enabled": False,                       # auto-translate after each OCR
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5",
        "target_lang": "English",
        "timeout": 60,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into a copy of base, recursing into nested dicts."""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        save_config(DEFAULTS)
        return copy.deepcopy(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            user = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Could not read %s (%s); using defaults.", path, e)
        return copy.deepcopy(DEFAULTS)
    # Fill in any keys added in newer versions.
    return _deep_merge(DEFAULTS, user)


def save_config(cfg: dict[str, Any]) -> None:
    path = config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError as e:
        log.error("Could not write config to %s: %s", path, e)


def resolve_model_dir(cfg: dict[str, Any]) -> Path:
    """Return the configured model directory, or the default if unset."""
    raw = (cfg.get("model_dir") or "").strip()
    return Path(raw) if raw else default_models_dir()

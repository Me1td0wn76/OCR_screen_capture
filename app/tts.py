"""Offline text-to-speech via pyttsx3 (Windows SAPI5).

Each utterance runs on its own short-lived engine in a worker thread. This
avoids pyttsx3's "run loop already started" issues when speaking repeatedly.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

log = logging.getLogger(__name__)


def list_voices() -> list[tuple[str, str]]:
    """Return [(voice_id, voice_name), ...] for installed SAPI5 voices."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        return [(v.id, v.name) for v in voices]
    except Exception:
        log.exception("could not list TTS voices")
        return []


class Speaker:
    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg.get("tts", {})
        self._lock = threading.Lock()

    def _resolve_voice_id(self, voices) -> Optional[str]:
        match = (self._cfg.get("voice_match") or "").lower()
        if not match:
            return None
        for v in voices:
            if match in v.name.lower() or match in v.id.lower():
                return v.id
        return None

    def _speak_blocking(self, text: str) -> None:
        import pyttsx3
        with self._lock:  # SAPI engines don't like concurrent use
            engine = pyttsx3.init()
            try:
                voice_id = self._resolve_voice_id(engine.getProperty("voices"))
                if voice_id:
                    engine.setProperty("voice", voice_id)
                engine.setProperty("rate", int(self._cfg.get("rate", 175)))
                engine.setProperty("volume", float(self._cfg.get("volume", 1.0)))
                engine.say(text)
                engine.runAndWait()
            finally:
                try:
                    engine.stop()
                except Exception:
                    pass

    def speak(self, text: str) -> None:
        """Speak text without blocking the caller."""
        text = (text or "").strip()
        if not text:
            return
        threading.Thread(
            target=self._safe_speak, args=(text,), name="tts-speak", daemon=True
        ).start()

    def _safe_speak(self, text: str) -> None:
        try:
            self._speak_blocking(text)
        except Exception:
            log.exception("TTS failed")

"""Translate text via a local OpenAI-compatible server (Ollama, LM Studio, ...).

Only used when a local LLM is running; otherwise translation is unavailable.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

log = logging.getLogger(__name__)


class Translator:
    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg.get("translate", {})

    @property
    def base_url(self) -> str:
        return self._cfg.get("base_url", "http://localhost:11434/v1").rstrip("/")

    def is_available(self) -> bool:
        """Quick reachability check against the /models endpoint."""
        try:
            r = requests.get(f"{self.base_url}/models", timeout=2)
            return r.ok
        except requests.RequestException:
            return False

    def translate(self, text: str, target_lang: str | None = None) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        target = target_lang or self._cfg.get("target_lang", "English")
        model = self._cfg.get("model", "qwen2.5")
        timeout = int(self._cfg.get("timeout", 60))
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a translation engine. Translate the user's text into "
                        f"{target}. Output only the translation, with no explanations, "
                        "notes, or quotation marks."
                    ),
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "stream": False,
        }
        r = requests.post(
            f"{self.base_url}/chat/completions", json=payload, timeout=timeout
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

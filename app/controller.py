"""Glue layer: clipboard image -> OCR -> clipboard text / TTS / translation."""
from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Optional

import pyperclip
from PIL import Image

from .clipboard_watch import ClipboardWatcher, grab_clipboard_image
from .config import load_config, save_config
from .ocr import OCREngine
from .paths import config_path
from .translate import Translator
from .tts import Speaker

log = logging.getLogger(__name__)

NotifyFn = Callable[[str, str], None]


def _preview(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class Controller:
    def __init__(self):
        self.cfg = load_config()
        self.ocr = OCREngine(self.cfg)
        self.tts = Speaker(self.cfg)
        self.translator = Translator(self.cfg)
        self.watcher = ClipboardWatcher(self.handle_image)
        self.last_text: str = ""
        self._notify: NotifyFn = lambda title, msg: None
        self._busy = threading.Lock()

    # -- wiring -------------------------------------------------------------
    def set_notifier(self, notifier: NotifyFn) -> None:
        self._notify = notifier

    def notify(self, title: str, message: str) -> None:
        if self.cfg.get("show_notifications", True):
            try:
                self._notify(title, message)
            except Exception:
                log.exception("notify failed")

    def start(self) -> None:
        self.watcher.start()
        self.watcher.set_enabled(self.cfg.get("auto_ocr", True))
        threading.Thread(target=self.ocr.warm_up, name="ocr-warmup", daemon=True).start()

    def shutdown(self) -> None:
        self.watcher.stop()

    # -- settings -----------------------------------------------------------
    def _save(self) -> None:
        save_config(self.cfg)

    def toggle_auto_ocr(self) -> None:
        self.cfg["auto_ocr"] = not self.cfg.get("auto_ocr", True)
        self.watcher.set_enabled(self.cfg["auto_ocr"])
        self._save()

    def toggle_tts(self) -> None:
        self.cfg["tts"]["speak_on_ocr"] = not self.cfg["tts"].get("speak_on_ocr", False)
        self._save()

    def toggle_translate(self) -> None:
        self.cfg["translate"]["enabled"] = not self.cfg["translate"].get("enabled", False)
        self._save()

    def toggle_copy(self) -> None:
        self.cfg["copy_to_clipboard"] = not self.cfg.get("copy_to_clipboard", True)
        self._save()

    def open_config(self) -> None:
        path = config_path()
        if not path.exists():
            self._save()
        try:
            os.startfile(str(path))  # noqa: S606 - intended on Windows
        except Exception:
            log.exception("could not open config file")

    # -- actions ------------------------------------------------------------
    def handle_image(self, img: Image.Image) -> None:
        """Called from the clipboard watcher thread; offload heavy work."""
        threading.Thread(
            target=self._process_image, args=(img,), name="ocr-job", daemon=True
        ).start()

    def manual_ocr_from_clipboard(self) -> None:
        img = grab_clipboard_image()
        if img is None:
            self.notify("OCR", "クリップボードに画像がありません")
            return
        self.handle_image(img)

    def speak_last(self) -> None:
        if self.last_text:
            self.tts.speak(self.last_text)
        else:
            self.notify("読み上げ", "読み上げる結果がまだありません")

    def translate_last(self) -> None:
        if not self.last_text:
            self.notify("翻訳", "翻訳する結果がまだありません")
            return
        threading.Thread(target=self._translate_and_copy, daemon=True).start()

    def _translate_and_copy(self) -> None:
        try:
            translated = self.translator.translate(self.last_text)
        except Exception as e:
            log.exception("translation failed")
            self.notify("翻訳エラー", f"LocalLLMに接続できません: {e}")
            return
        self._copy_text(translated)
        self.last_text = translated
        self.notify("翻訳完了 (コピー済み)", _preview(translated))

    # -- internals ----------------------------------------------------------
    def _copy_text(self, text: str) -> None:
        if not self.cfg.get("copy_to_clipboard", True):
            return
        try:
            pyperclip.copy(text)
            self.watcher.mark_self_copy()  # don't re-trigger on our own write
        except Exception:
            log.exception("clipboard copy failed")

    def _process_image(self, img: Image.Image) -> None:
        if not self._busy.acquire(blocking=False):
            return  # an OCR job is already running; skip this one
        try:
            self.notify("OCR", "認識中…")
            text = self.ocr.recognize(img)
            if not text:
                self.notify("OCR", "文字を検出できませんでした")
                return
            self.last_text = text
            self._copy_text(text)

            preview = text
            if self.cfg["translate"].get("enabled", False):
                try:
                    translated = self.translator.translate(text)
                    combined = f"{text}\n---\n{translated}"
                    self._copy_text(combined)
                    self.last_text = combined
                    preview = translated
                except Exception as e:
                    log.exception("auto-translate failed")
                    self.notify("翻訳エラー", f"LocalLLM未接続: {e}")

            self.notify("OCR完了 (コピー済み)", _preview(preview))
            if self.cfg["tts"].get("speak_on_ocr", False):
                self.tts.speak(text)
        finally:
            self._busy.release()

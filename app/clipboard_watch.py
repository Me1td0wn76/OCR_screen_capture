"""Watch the Windows clipboard for new images and copy text back.

This is how we hook into Win+Shift+S: the Snipping Tool places the snip on
the clipboard, we notice the new image and run OCR on it.
"""
from __future__ import annotations

import ctypes
import hashlib
import logging
import threading
import time
from typing import Callable, Optional

from PIL import Image, ImageGrab

log = logging.getLogger(__name__)

_user32 = ctypes.windll.user32


def _clipboard_sequence() -> int:
    """Monotonic counter that changes whenever the clipboard is updated."""
    return _user32.GetClipboardSequenceNumber()


def grab_clipboard_image() -> Optional[Image.Image]:
    """Return the clipboard image as a PIL Image, or None if there isn't one."""
    try:
        data = ImageGrab.grabclipboard()
    except Exception as e:  # clipboard can be transiently locked
        log.debug("grabclipboard failed: %s", e)
        return None
    if isinstance(data, Image.Image):
        return data
    return None


def _image_fingerprint(img: Image.Image) -> str:
    return hashlib.md5(img.tobytes()).hexdigest()


class ClipboardWatcher:
    """Polls the clipboard sequence number and fires a callback on new images."""

    def __init__(self, on_image: Callable[[Image.Image], None], poll_interval: float = 0.5):
        self._on_image = on_image
        self._poll = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._enabled = threading.Event()
        self._last_seq = _clipboard_sequence()
        self._last_fp: Optional[str] = None

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            # Don't OCR whatever happens to be on the clipboard right now.
            self._last_seq = _clipboard_sequence()
            self._enabled.set()
        else:
            self._enabled.clear()

    def mark_self_copy(self) -> None:
        """Call right after we put our own text on the clipboard, so the
        resulting sequence bump is not mistaken for a new snip."""
        self._last_seq = _clipboard_sequence()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="clipboard-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            time.sleep(self._poll)
            if not self._enabled.is_set():
                continue
            seq = _clipboard_sequence()
            if seq == self._last_seq:
                continue
            self._last_seq = seq
            img = grab_clipboard_image()
            if img is None:
                continue  # clipboard changed but it wasn't an image (e.g. text)
            fp = _image_fingerprint(img)
            if fp == self._last_fp:
                continue  # same image as last time
            self._last_fp = fp
            try:
                self._on_image(img)
            except Exception:
                log.exception("clipboard image handler failed")

"""Native window UI via pywebview.

The cute HTML/CSS pages (served by the local Flask server) are shown inside a
native desktop window — no browser is opened, and the localhost server is only
ever consumed by this embedded WebView. The window stays alive (hidden) so the
tray app remains resident; closing it just hides it.

pywebview must run its event loop on the main thread, so ``run_blocking`` is
called last from main(); the tray icon runs on its own thread.
"""
from __future__ import annotations

import logging
import threading

import webview

log = logging.getLogger(__name__)


class JsApi:
    """Methods callable from the page as ``window.pywebview.api.<name>()``."""

    def pick_folder(self) -> str:
        try:
            wins = webview.windows
            if not wins:
                return ""
            result = wins[0].create_file_dialog(webview.FOLDER_DIALOG)
            if result:
                return result[0]
        except Exception:
            log.exception("folder dialog failed")
        return ""


class WebViewUI:
    def __init__(self, controller, base_url: str):
        self.c = controller
        self.base_url = base_url.rstrip("/")
        self.api = JsApi()
        self.window = None
        self._quitting = False
        self._started = threading.Event()

    def run_blocking(self, show_setup: bool = False) -> None:
        """Create the window and run the GUI loop. Blocks the main thread."""
        start_path = "/setup" if show_setup else "/settings"
        self.window = webview.create_window(
            "OCR スクリーン転写",
            url=self.base_url + start_path,
            js_api=self.api,
            width=620,
            height=760,
            hidden=not show_setup,
            background_color="#fff1f6",
        )
        self.window.events.closing += self._on_closing
        self._started.set()
        webview.start()

    def _on_closing(self):
        if self._quitting:
            return True       # allow the window to close (app is exiting)
        self.window.hide()    # otherwise keep resident; just hide
        return False

    def _navigate_and_show(self, path: str) -> None:
        if not self.window:
            return
        try:
            self.window.load_url(self.base_url + path)
            self.window.show()
        except Exception:
            log.exception("could not show window")

    def show_settings(self) -> None:
        self._navigate_and_show("/settings")

    def show_setup(self) -> None:
        self._navigate_and_show("/setup")

    def quit(self) -> None:
        self._quitting = True
        try:
            if self.window:
                self.window.destroy()
        except Exception:
            log.exception("error destroying window")

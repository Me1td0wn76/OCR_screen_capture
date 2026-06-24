"""Entry point for the OCR screen-capture transcription tray app.

Run with:  python main.py
Build exe: see build.bat / ocr_tool.spec

The source lives under the app/ package; this thin launcher wires it together.
The tray icon runs on its own thread while pywebview owns the main thread.
"""
from __future__ import annotations

import logging
import os
import sys

from app.controller import Controller
from app.paths import app_dir
from app.tray import TrayApp
from app.web.server import WebServer
from app.webview_ui import WebViewUI


def _setup_logging() -> None:
    log_file = app_dir() / "ocr_tool.log"
    handlers: list[logging.Handler] = [logging.FileHandler(log_file, encoding="utf-8")]
    if not getattr(sys, "frozen", False):
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> int:
    _setup_logging()
    log = logging.getLogger("main")
    log.info("starting OCR tray app")
    try:
        controller = Controller()

        web = WebServer(controller)      # local pages + JSON API (localhost only)
        web.start()
        log.info("web server at %s", web.url)

        ui = WebViewUI(controller, web.url)
        controller.set_ui(ui)

        tray = TrayApp(controller, ui)
        tray.start()                     # tray icon on its own thread

        # pywebview must own the main thread; this blocks until the user quits.
        ui.run_blocking(show_setup=controller.needs_setup())
    except Exception:
        log.exception("fatal error")
        return 1
    log.info("exited")
    return 0


if __name__ == "__main__":
    code = main()
    logging.shutdown()
    # pywebview's .NET (pythonnet) runtime can leave a non-daemon thread that
    # keeps the process alive after the window closes; force a clean exit.
    os._exit(code)

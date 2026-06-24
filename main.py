"""Entry point for the OCR screen-capture transcription tray app.

Run with:  python main.py
Build exe: see build.bat / ocr_tool.spec

The source lives under the app/ package; this thin launcher wires it together.
"""
from __future__ import annotations

import logging
import sys

from app.controller import Controller
from app.paths import app_dir
from app.tray import TrayApp
from app.web.server import WebUI


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
        web = WebUI(controller)          # local Flask settings/setup server
        web.start()
        controller.set_web_url(web.url)
        tray = TrayApp(controller, web_url=web.url)
        # First launch (no model configured yet) -> open the setup wizard.
        if controller.needs_setup():
            web.open_in_browser("/setup")
        tray.run()                       # blocks until the user quits
    except Exception:
        log.exception("fatal error")
        return 1
    log.info("exited")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Entry point for the OCR screen-capture transcription tray app.

Run with:  python main.py
Build exe: see build.bat / ocr_tool.spec

The source lives under the app/ package; this thin launcher wires it together.
"""
from __future__ import annotations

import logging
import sys

from app.controller import Controller
from app.gui import UIManager
from app.paths import app_dir
from app.tray import TrayApp


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
        ui = UIManager(controller)       # native CustomTkinter settings/setup
        ui.start()
        controller.set_ui(ui)
        tray = TrayApp(controller, ui)
        # First launch (no model configured yet) -> show the setup wizard.
        if controller.needs_setup():
            ui.show_setup()
        tray.run()                       # blocks until the user quits
    except Exception:
        log.exception("fatal error")
        return 1
    log.info("exited")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

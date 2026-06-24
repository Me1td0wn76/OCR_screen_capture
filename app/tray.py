"""System-tray UI (pystray) wrapping the Controller."""
from __future__ import annotations

import logging

import pystray
from PIL import Image, ImageDraw
from pystray import Menu, MenuItem

from .controller import Controller

log = logging.getLogger(__name__)


def _make_icon_image() -> Image.Image:
    img = Image.new("RGB", (64, 64), (32, 38, 52))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, 57, 57], radius=12, outline=(120, 180, 255), width=3)
    d.text((14, 20), "OCR", fill=(235, 240, 250))
    return img


class TrayApp:
    def __init__(self, controller: Controller, ui=None):
        self.c = controller
        self.ui = ui
        self.icon = pystray.Icon(
            "ocr_tool", _make_icon_image(), "OCR スクリーン転写", menu=self._build_menu()
        )
        self.c.set_notifier(self._notify)

    def _notify(self, title: str, message: str) -> None:
        try:
            self.icon.notify(message, title)
        except Exception:
            log.debug("tray notify unavailable", exc_info=True)

    def _open_settings(self) -> None:
        ui = self.ui or self.c.ui
        if ui:
            ui.show_settings()
        else:
            self.c.open_config()

    def _build_menu(self) -> Menu:
        c = self.c
        return Menu(
            MenuItem("クリップボードの画像をOCR", lambda: c.manual_ocr_from_clipboard()),
            MenuItem("最後の結果を読み上げる", lambda: c.speak_last()),
            MenuItem("最後の結果を翻訳", lambda: c.translate_last()),
            Menu.SEPARATOR,
            MenuItem(
                "自動OCR (クリップボード監視)",
                lambda: c.toggle_auto_ocr(),
                checked=lambda item: c.cfg.get("auto_ocr", True),
            ),
            MenuItem(
                "テキストをクリップボードにコピー",
                lambda: c.toggle_copy(),
                checked=lambda item: c.cfg.get("copy_to_clipboard", True),
            ),
            MenuItem(
                "OCR結果を読み上げる (TTS)",
                lambda: c.toggle_tts(),
                checked=lambda item: c.cfg["tts"].get("speak_on_ocr", False),
            ),
            MenuItem(
                "自動翻訳 (LocalLLM)",
                lambda: c.toggle_translate(),
                checked=lambda item: c.cfg["translate"].get("enabled", False),
            ),
            Menu.SEPARATOR,
            MenuItem("設定を開く", lambda: self._open_settings(), default=True),
            MenuItem("設定ファイル(config.json)を開く", lambda: c.open_config()),
            MenuItem("終了", self._quit),
        )

    def _quit(self) -> None:
        self.c.shutdown()
        self.icon.stop()

    def run(self) -> None:
        self.c.start()
        self.icon.run()

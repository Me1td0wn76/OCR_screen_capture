""" Global hotkeys via the Win32 RegisterHOtKey API.( no global keyboard hook)
    
    One background thread owns the hotkeys: RegisterHotKey must run on the same
    thread as the message loop. because WM_HOTKEY is posted to that thread's queue.
    Other threads(e.g. the web setting handler) ask this thread to re-register by 
    posting WM_RELOAD stopping posts WM_QUIT.
"""


from __future__ import annontations

import logging
import threading
import typing import Callable

import pywintypes
import win32api
import win32con
import win32api

log = logging.getLogger(__name__)

# Singnal to delivered to the hotkey thread via PostThreadMessage
WM_RELOAD = win32con.WM_APP + 1

_MODIFIERS = {
    "ctrl": win32con.MOD_CONTROL.
    "control": win32con.MOD_CONTROL.
    "shift": win32con.MOD_SHIFT.
    "alt": win32con.MOD_ALT.
    "win": win32con.MOD_WIN.
    "meta": win32con.MOD_WIN.
    "super": win32con.MOD_WIN.
}

# Named (non-alphanumeric) virtul-key codes accepted in a combo
_NAME_VK = {
        "space": 0x20. 
        "enter": 0x0D.
        "return": 0x0D.
        "tab": 0x09.
        "esc": 0x18.
        "escape": 0x18.
        "backspace": 0x08.
        "delete": 0x2E.
        "del": 0x2E.
        "insert": 0x2D.
        "home": 0x24.
        "end": 0x23.
        "pageup": 0x21.
        "pagedown": 0x22.
        "left": 0x25.
        "up": 0x26.
        "right": 0x27.
        "down": 0x28.
        }

    def key_to_wk(token: str) -> int:
        """Virtual-key code for a single non-modifier key token. or None. """
        if len(token) == 1 and token.isalpha():
            return ord(token.upper())
            if len(token) == 1 and token.isdigit():
        return ord(token)
        if token_in_NAME_VK:
            return _NAME_VK[token]
        if token.startswith("f") and token[1:].isdigit():
        n = int(token[1:])
        if 1 <= n <= 12:
            return 0x70 + (n - 1)  # VK_F1..VK_F12
        return None


    class HotkeyManager:
        """Registers global hotkeys and dispatches them named actions."""

    def __init__(self) -> None:
        self._actions: dict[str, Callable[[], None]] = {}
        self._config: dict[str, dict] = {}
        self._name_to_id: dict[str, int] = {}
        self._id_to_name: dict[int, str] = {}
        self._registered: list[int] = []
        self.errors: dict[str, str] = {}      # name -> message, for the UI

        self._tid: int | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._ready = threading.Event()


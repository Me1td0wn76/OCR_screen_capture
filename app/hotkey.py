"""Global hotkeys via the Win32 RegisterHotKey API (no global keyboard hook).

One background thread owns the hotkeys: RegisterHotKey must run on the same
thread as the message loop, because WM_HOTKEY is posted to that thread's queue.
Other threads (e.g. the web settings handler) ask this thread to re-register by
posting WM_RELOAD; stopping posts WM_QUIT.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

import pywintypes
import win32api
import win32con
import win32gui

log = logging.getLogger(__name__)

# Signal delivered to the hotkey thread via PostThreadMessage.
WM_RELOAD = win32con.WM_APP + 1

_MODIFIERS = {
    "ctrl": win32con.MOD_CONTROL, "control": win32con.MOD_CONTROL,
    "shift": win32con.MOD_SHIFT,
    "alt": win32con.MOD_ALT,
    "win": win32con.MOD_WIN, "meta": win32con.MOD_WIN, "super": win32con.MOD_WIN,
}

# Named (non-alphanumeric) virtual-key codes accepted in a combo.
_NAMED_VK = {
    "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09,
    "esc": 0x1B, "escape": 0x1B, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "insert": 0x2D, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
}


def _key_to_vk(token: str) -> int | None:
    """Virtual-key code for a single non-modifier key token, or None."""
    if len(token) == 1 and token.isalpha():
        return ord(token.upper())
    if len(token) == 1 and token.isdigit():
        return ord(token)
    if token in _NAMED_VK:
        return _NAMED_VK[token]
    if token.startswith("f") and token[1:].isdigit():
        n = int(token[1:])
        if 1 <= n <= 12:
            return 0x70 + (n - 1)  # VK_F1..VK_F12
    return None


def parse_combo(combo: str) -> tuple[int, int]:
    """Parse 'ctrl+shift+o' into (modifiers, vk). Raises ValueError if invalid.

    Requires >=1 modifier (so a bare key can't hijack normal typing) and exactly
    one key. MOD_NOREPEAT is OR-ed in so holding the combo fires only once.
    """
    mods = 0
    vk: int | None = None
    for raw in combo.split("+"):
        token = raw.strip().lower()
        if not token:
            continue
        if token in _MODIFIERS:
            mods |= _MODIFIERS[token]
            continue
        if vk is not None:
            raise ValueError(f"combo has more than one key: {combo!r}")
        vk = _key_to_vk(token)
        if vk is None:
            raise ValueError(f"unknown key in combo: {token!r}")
    if vk is None:
        raise ValueError(f"combo has no key: {combo!r}")
    if mods == 0:
        raise ValueError(f"combo needs at least one modifier: {combo!r}")
    return mods | win32con.MOD_NOREPEAT, vk


class HotkeyManager:
    """Registers global hotkeys and dispatches them to named actions."""

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

    # -- public API ---------------------------------------------------------
    def start(self, actions: dict[str, Callable[[], None]]) -> None:
        """Start the hotkey thread. `actions` maps a name to a callback."""
        self._actions = dict(actions)
        # Stable hotkey id (1..N) per known action.
        self._name_to_id = {name: i + 1 for i, name in enumerate(sorted(actions))}
        self._id_to_name = {i: n for n, i in self._name_to_id.items()}
        self._thread = threading.Thread(target=self._run, name="hotkeys", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def apply(self, config: dict[str, dict]) -> None:
        """Re-register from config: {name: {"enabled": bool, "combo": str}}."""
        with self._lock:
            self._config = {k: dict(v) for k, v in (config or {}).items()}
        if self._tid is not None:
            win32api.PostThreadMessage(self._tid, WM_RELOAD, 0, 0)

    def stop(self) -> None:
        if self._tid is not None:
            win32api.PostThreadMessage(self._tid, win32con.WM_QUIT, 0, 0)

    # -- thread internals ---------------------------------------------------
    def _run(self) -> None:
        self._tid = win32api.GetCurrentThreadId()
        self._ready.set()
        self._reregister()
        try:
            while True:
                rc, msg = win32gui.GetMessage(None, 0, 0)
                if rc in (0, -1):                 # WM_QUIT / error
                    break
                message, wparam = msg[1], msg[2]
                if message == win32con.WM_HOTKEY:
                    self._dispatch(wparam)
                elif message == WM_RELOAD:
                    self._reregister()
        finally:
            self._unregister_all()

    def _dispatch(self, hotkey_id: int) -> None:
        name = self._id_to_name.get(hotkey_id)
        fn = self._actions.get(name) if name else None
        if not fn:
            return
        try:
            fn()
        except Exception:
            log.exception("hotkey action %s failed", name)

    def _reregister(self) -> None:
        self._unregister_all()
        with self._lock:
            config = dict(self._config)
        self.errors.clear()
        for name, hk in config.items():
            if name not in self._name_to_id or not hk.get("enabled"):
                continue
            combo = str(hk.get("combo", "")).strip()
            if not combo:
                continue
            try:
                mods, vk = parse_combo(combo)
            except ValueError as e:
                self.errors[name] = str(e)
                log.warning("invalid hotkey %s=%r: %s", name, combo, e)
                continue
            hotkey_id = self._name_to_id[name]
            try:
                win32gui.RegisterHotKey(0, hotkey_id, mods, vk)
                self._registered.append(hotkey_id)
                log.info("registered hotkey %s = %s", name, combo)
            except pywintypes.error as e:
                self.errors[name] = "このキーは使用中です"
                log.warning("RegisterHotKey failed for %s=%r: %s", name, combo, e)

    def _unregister_all(self) -> None:
        for hotkey_id in self._registered:
            try:
                win32gui.UnregisterHotKey(0, hotkey_id)
            except pywintypes.error:
                pass
        self._registered.clear()

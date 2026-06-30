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


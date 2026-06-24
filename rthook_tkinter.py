"""PyInstaller runtime hook: point Tcl/Tk at the bundled data dir.

The standard tkinter hook didn't fire for this (scoop) Python layout, so we
bundle Tcl/Tk manually and set TCL_LIBRARY / TK_LIBRARY before tkinter loads.
"""
import os
import sys

if hasattr(sys, "_MEIPASS"):
    _tcl = os.path.join(sys._MEIPASS, "tcl")
    os.environ.setdefault("TCL_LIBRARY", os.path.join(_tcl, "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", os.path.join(_tcl, "tk8.6"))

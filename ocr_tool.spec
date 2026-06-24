# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the OCR tray app.

Build:  pyinstaller ocr_tool.spec
Output: dist/OCR_Transcribe/OCR_Transcribe.exe  (one-folder build)

A one-folder build is used (not --onefile) because onnxruntime + opencv start
noticeably faster when not unpacked to a temp dir on every launch.
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# --- Tkinter (manual bundling) -----------------------------------------------
# PyInstaller's automatic tkinter hook does not fire for this Python layout, so
# we add the package, the _tkinter extension, the Tcl/Tk DLLs, and the Tcl/Tk
# data dir explicitly. rthook_tkinter.py points TCL_LIBRARY/TK_LIBRARY at it.
_base = sys.base_prefix
binaries += [
    (os.path.join(_base, "DLLs", "_tkinter.pyd"), "."),
    (os.path.join(_base, "DLLs", "tcl86t.dll"), "."),
    (os.path.join(_base, "DLLs", "tk86t.dll"), "."),
]
datas += [
    (os.path.join(_base, "Lib", "tkinter"), "tkinter"),
    (os.path.join(_base, "tcl"), "tcl"),
]

# Bundle packages that carry data files / native libs (RapidOCR, CustomTkinter).
for pkg in ("rapidocr_onnxruntime", "onnxruntime", "shapely", "customtkinter"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Japanese model as an offline default (other languages download on demand).
datas += [("models/japan_rec_crnn_v2.onnx", "models")]

# Modules PyInstaller's static analysis tends to miss.
hiddenimports += [
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
    "pystray._win32",
    "comtypes",
    "win32com",
    "win32com.client",
    "pyclipper",
    "cv2",
    "darkdetect",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["rthook_tkinter.py"],
    excludes=["matplotlib", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OCR_Transcribe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # tray app: no console window
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="OCR_Transcribe",
)

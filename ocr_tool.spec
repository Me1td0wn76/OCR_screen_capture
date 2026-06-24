# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the OCR tray app.

Build:  pyinstaller ocr_tool.spec
Output: dist/OCR_Transcribe/OCR_Transcribe.exe  (one-folder build)

A one-folder build is used (not --onefile) because onnxruntime + opencv start
noticeably faster when not unpacked to a temp dir on every launch.
"""
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Bundle packages that carry data files / native libs RapidOCR needs.
for pkg in ("rapidocr_onnxruntime", "onnxruntime", "shapely"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Our Japanese recognition model (read at runtime from models/).
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
]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest"],
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

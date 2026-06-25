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

# Bundle packages that carry data files / native libs. collect_all("rapidocr")
# pulls in its bundled PP-OCRv6 ONNX models + yaml configs (config.yaml,
# default_models.yaml), so OCR works offline with no model download at runtime.
for pkg in ("rapidocr", "onnxruntime", "shapely", "flask", "webview"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Web UI templates/static (loaded at runtime from _MEIPASS/app/web/...).
datas += [
    ("app/web/templates", "app/web/templates"),
    ("app/web/static", "app/web/static"),
]

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
    # pywebview Windows backend (Edge WebView2 via pythonnet).
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr_loader",
    "pythonnet",
    "bottle",
]

a = Analysis(
    ["main.py"],
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
    version="version_info.txt",  # embeds product name / copyright / version
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="OCR_Transcribe",
)

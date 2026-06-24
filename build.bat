@echo off
REM Build OCR_Transcribe.exe (one-folder) with PyInstaller.
REM Run from the project root after creating/activating the venv.

setlocal
set VENV_PY=venv\Scripts\python.exe

if not exist "%VENV_PY%" (
    echo [!] venv not found. Create it first:  python -m venv venv
    exit /b 1
)

echo [*] Installing build/runtime dependencies...
"%VENV_PY%" -m pip install -r requirements.txt pyinstaller || exit /b 1

echo [*] Building exe...
"%VENV_PY%" -m PyInstaller --noconfirm ocr_tool.spec || exit /b 1

echo.
echo [+] Done. Launch: dist\OCR_Transcribe\OCR_Transcribe.exe
endlocal

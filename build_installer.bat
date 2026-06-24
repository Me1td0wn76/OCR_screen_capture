@echo off
REM Build the per-user installer with Inno Setup.
REM Requires Inno Setup 6 (https://jrsoftware.org/isdl.php).
REM Run build.bat first so dist\OCR_Transcribe\ exists.

setlocal
if not exist "dist\OCR_Transcribe\OCR_Transcribe.exe" (
    echo [!] dist\OCR_Transcribe not found. Run build.bat first.
    exit /b 1
)

set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    echo [!] ISCC.exe not found. Install Inno Setup 6: https://jrsoftware.org/isdl.php
    exit /b 1
)

%ISCC% installer.iss || exit /b 1
echo.
echo [+] Installer created: installer_out\OCR_Transcribe_Setup.exe
endlocal

; Inno Setup script — per-user installer (no admin / no UAC prompt).
; Installs to %LocalAppData%\Programs\OCR_SCREEN_CAPTURE_TRANSCRIPTION.
;
; Build first:  build.bat            (produces dist\OCR_Transcribe\)
; Then compile: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;          or:  build_installer.bat

#define MyAppName "OCR Screen Capture Transcription"
#define MyAppExeName "OCR_Transcribe.exe"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "OCR Tool"

[Setup]
AppId={{C0B5552E-0942-4556-876C-D33C5739E55E}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; Per-user install -> LocalAppData\Programs, no administrator rights required.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\OCR_SCREEN_CAPTURE_TRANSCRIPTION
DisableProgramGroupPage=yes
DisableDirPage=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=installer_out
OutputBaseFilename=OCR_Transcribe_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにアイコンを作成する"; Flags: unchecked
Name: "startupicon"; Description: "Windows起動時に自動的に開始する"; Flags: unchecked

[Files]
Source: "dist\OCR_Transcribe\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Optional auto-start at logon (per-user Run key, no UAC).
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "OCR_Transcribe"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Tasks: startupicon; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "今すぐ起動する"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove runtime files the app generated next to the exe.
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\ocr_tool.log"
Type: filesandordirs; Name: "{app}\models"

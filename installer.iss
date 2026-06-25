; Inno Setup script — per-user installer (no admin / no UAC prompt).
; Installs to %LocalAppData%\Programs\OCR_SCREEN_CAPTURE_TRANSCRIPTION.
;
; Build first:  build.bat            (produces dist\OCR_Transcribe\)
; Then compile: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;          or:  build_installer.bat

#define MyAppName "OCR Screen Capture Transcription"
#define MyAppExeName "OCR_Transcribe.exe"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "Me1td0wn76"
#define MyAppCopyright "Copyright (C) 2026 Me1td0wn76 (MIT License)"

[Setup]
AppId={{C0B5552E-0942-4556-876C-D33C5739E55E}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright={#MyAppCopyright}

; Version resource of the generated Setup.exe (fills "Copyright", file version).
VersionInfoVersion=0.3.0.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright={#MyAppCopyright}
VersionInfoDescription={#MyAppName} Setup

; Per-user install -> LocalAppData\Programs, no administrator rights required.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\OCR_SCREEN_CAPTURE_TRANSCRIPTION
DisableProgramGroupPage=yes
DisableDirPage=yes
LicenseFile=LICENSE

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=installer_out
OutputBaseFilename=OCR_Transcribe_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; The tray app doesn't cooperate with the Restart Manager, so we don't rely on
; it; instead PrepareToInstall (see [Code]) force-terminates the running process
; before any files are touched. Keep this off to avoid silent-install aborts.
CloseApplications=no

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにアイコンを作成する"; Flags: unchecked
Name: "startupicon"; Description: "Windows起動時に自動的に開始する"; Flags: unchecked

[Files]
Source: "dist\OCR_Transcribe\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; On upgrade, wipe the previous program files BEFORE the new ones are copied so
; no orphaned modules from an older version linger (e.g. renamed/removed DLLs or
; model files). This runs before [Files]. User data (config.json, ocr_tool.log)
; is intentionally preserved across upgrades.
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\{#MyAppExeName}"
Type: files; Name: "{app}\LICENSE"
Type: files; Name: "{app}\THIRD_PARTY_NOTICES.md"

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

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  // The tray app keeps its own files (in {app}) locked while running. Force it
  // to close before [InstallDelete]/[Files] run, so an upgrade can replace the
  // old version cleanly. Safe on a per-user install (own process, no admin).
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM {#MyAppExeName} /F',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // Give the OS a moment to release file handles after the process exits.
  Sleep(800);
  Result := '';
end;

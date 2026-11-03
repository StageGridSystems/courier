; Inno Setup script for Courier by StageGrid Systems.
; Builds Courier-Setup-<version>.exe from the PyInstaller ONEDIR output.
;
; Compile (from repo root, after PyInstaller):
;   ISCC /DMyAppVersion=0.1.0 packaging\windows\courier.iss
;
; User data, config, and OAuth tokens live under the per-user app data folder
; (platformdirs: %LOCALAPPDATA%\StageGrid Systems\Courier) and are intentionally
; left alone on upgrade and uninstall.

#define MyAppName "Courier"
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "StageGrid Systems"
#define MyAppExeName "Courier.exe"
; Stable AppUserModelID (must match courier.branding.APP_ID and app startup).
#define MyAppUserModelID "systems.stagegrid.courier"
; Fixed AppId so upgrades replace the previous install in place.
#define MyAppId "{{1e6035e6-59f9-5f5c-92da-74732fe1d7e9}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/StageGridSystems/courier
AppSupportURL=https://github.com/StageGridSystems/courier
AppUpdatesURL=https://github.com/StageGridSystems/courier/releases
DefaultDirName={autopf}\StageGrid-Systems\Courier
DefaultGroupName=StageGrid Systems
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist\windows
OutputBaseFilename=Courier-Setup-{#MyAppVersion}
SetupIconFile=courier.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) StageGrid Systems
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
; Do not touch per-user data under {localappdata}\StageGrid Systems\Courier

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; ONEDIR tree produced by PyInstaller (dist\windows\Courier\...)
Source: "..\..\dist\windows\Courier\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; \
    AppUserModelID: "{#MyAppUserModelID}"; Comment: "Courier by StageGrid Systems"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; \
    AppUserModelID: "{#MyAppUserModelID}"; Tasks: desktopicon; \
    Comment: "Courier by StageGrid Systems"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Courier"; \
    Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"

[UninstallDelete]
; Only remove empty leftover dirs under the install root; never user data.
Type: dirifempty; Name: "{app}"

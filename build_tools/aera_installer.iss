; Inno Setup script for AERA Agent – Windows EXE installer
; Compile with: iscc build_tools\aera_installer.iss
; Output: dist\AERA-Setup-0.0.1.exe

#define MyAppName "AERA Agent"
#define MyAppVersion "0.0.1"
#define MyAppPublisher "AERA"
#define MyAppURL "https://github.com/manoj-dahal/Aera"
#define MyAppExeName "AERA.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-47G8-H9I0-J1K2L3M4N5O6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=AERA-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\aera_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Main bundle – onedir
Source: "..\dist\AERA\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\assets\aera_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; Also include onefile exe if exists as alternative
Source: "..\dist\AERA.exe"; DestDir: "{app}"; DestName: "AERA-onefile.exe"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\dist\AERA.pyz"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\aera_icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\aera_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch AERA Agent"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*"

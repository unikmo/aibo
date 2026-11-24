; AIBO Windows installer. Public distribution REQUIRES Authenticode signing.
#define MyAppName "AIBO Control Centre"
#define MyAppVersion "3.0"
#define MyAppExeName "AIBO.exe"
[Setup]
AppId={{C9EDE55D-27C8-4F24-947B-FDE32FF15B22}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\AIBO
DefaultGroupName=AIBO
OutputDir=..\..\dist\installer
OutputBaseFilename=AIBO-Control-Centre-Windows-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\AIBO.exe
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
[Files]
Source: "..\..\dist\AIBO\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\AIBO Control Centre"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AIBO Control Centre"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch AIBO"; Flags: nowait postinstall skipifsilent

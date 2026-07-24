#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#define MyAppName "CleanDrop"
#define MyAppPublisher "CleanDrop Contributors"
#define MyAppURL "https://github.com/Omidzamani11/CleanDrop"
#define MyAppExeName "CleanDrop.exe"

[Setup]
AppId={{9D57A323-7B7D-42EF-A547-4207B00F761B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\CleanDrop
DefaultGroupName=CleanDrop
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename=CleanDrop-Setup-{#MyAppVersion}
SetupIconFile=..\src\cleandrop\resources\cleandrop-icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\CleanDrop.exe
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=CleanDrop installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\CleanDrop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CleanDrop"; Filename: "{app}\CleanDrop.exe"
Name: "{group}\CleanDrop CLI"; Filename: "{cmd}"; Parameters: "/K ""{app}\cleandrop-cli.exe"" doctor"; WorkingDir: "{app}"
Name: "{group}\Uninstall CleanDrop"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CleanDrop"; Filename: "{app}\CleanDrop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CleanDrop.exe"; Description: "{cm:LaunchProgram,CleanDrop}"; Flags: nowait postinstall skipifsilent

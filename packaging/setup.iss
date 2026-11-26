#ifndef AppVersion
#define AppVersion "0.4.0"
#endif
[Setup]
AppId={{6EF1507E-4C51-46B0-93DE-894D92BEBFE1}
AppName=MD to PDF
AppVersion={#AppVersion}
AppPublisher=MD to PDF
DefaultDirName={autopf}\MD to PDF
DefaultGroupName=MD to PDF
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..
OutputBaseFilename=MD-to-PDF-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\MD-to-PDF.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
[Files]
Source: "..\dist\MD-to-PDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{commonprograms}\MD to PDF"; Filename: "{app}\MD-to-PDF.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\MD to PDF"; Filename: "{app}\MD-to-PDF.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\MD-to-PDF.exe"; Description: "{cm:LaunchProgram,MD to PDF}"; Flags: nowait postinstall skipifsilent runasoriginaluser

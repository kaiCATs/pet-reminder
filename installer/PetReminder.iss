#define MyAppName "Pet Reminder"
#ifndef MyAppVersion
#define MyAppVersion "11.0.0"
#endif
#define MyAppPublisher "Pet Reminder"
#define MyAppExeName "PetReminder.exe"

[Setup]
AppId={{F5A8C8E4-9A6E-4F14-9D4E-6A7E5B19E8C2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/kaiCATs/pet-reminder
AppSupportURL=https://github.com/kaiCATs/pet-reminder/issues
AppUpdatesURL=https://github.com/kaiCATs/pet-reminder/releases
DefaultDirName={localappdata}\Programs\PetReminder
DefaultGroupName={#MyAppName}
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\icon.ico
VersionInfoCompany=PetReminder Studio
VersionInfoDescription=Pet Reminder desktop companion
VersionInfoProductName=Pet Reminder
VersionInfoProductVersion={#MyAppVersion}
VersionInfoTextVersion={#MyAppVersion}
VersionInfoCopyright=PetReminder Studio
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=PetReminder_Setup_v{#MyAppVersion}_GUI
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
Uninstallable=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные ярлыки:"

[Files]
Source: "..\dist\PetReminder.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Pet Reminder"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Pet Reminder"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить Pet Reminder"; Flags: nowait postinstall skipifsilent

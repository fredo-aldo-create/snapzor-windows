; Snapzor.iss — Installeur Inno Setup
; Compiler avec Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; Le résultat est un Snapzor_Setup_1.0.0.exe dans Output\

#define MyAppName "Snapzor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Snapzor"
#define MyAppExeName "Snapzor.exe"

[Setup]
AppId={{8F3D7A1E-0B2F-4F5A-9C5E-SNAPZOR000001}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=Snapzor_Setup_{#MyAppVersion}
SetupIconFile=Snapzor.ico
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer une icône sur le &Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked
Name: "startupicon"; Description: "Lancer Snapzor au &démarrage de Windows"; GroupDescription: "Options :"; Flags: unchecked

[Files]
Source: "dist\Snapzor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

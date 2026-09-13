; SketchBook Windows installer (Inno Setup 6).
; Compiled by scripts/package_release.py via ISCC.exe
;   ISCC /DMyAppVersion=0.2.0 installer\sketchbook.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "SketchBook"
#define MyAppPublisher "SketchBook"
#define MyAppExeName "SketchBook.exe"

[Setup]
AppId={{A7E4C2B1-8F3D-4A19-9E6C-1B5D8F2A4C70}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=SketchBook-Setup-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\gui\ressources\icones\SketchBook.ico
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\SketchBook\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; AppUserModelID: "LeoTsunami.SketchBook"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; AppUserModelID: "LeoTsunami.SketchBook"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DataDirPage: TInputDirWizardPage;

function ConfigPath: String;
begin
  Result := ExpandConstant('{%USERPROFILE}\.sketchbook_config.json');
end;

function JsonEscapePath(const Value: String): String;
begin
  Result := Value;
  StringChangeEx(Result, '\', '\\', True);
  StringChangeEx(Result, '"', '\"', True);
end;

procedure InitializeWizard;
begin
  DataDirPage := CreateInputDirPage(
    wpSelectDir,
    'Image library location',
    'Where should SketchBook store your images and tags?',
    'This folder holds imported images, config\library.db and sessions. ' +
    'No image library is bundled with the installer. ' +
    'On an update, an existing library folder is left unchanged.',
    False,
    ''
  );
  DataDirPage.Add('');
  DataDirPage.Values[0] := ExpandConstant('{userdocs}\SketchBook');
end;

procedure WriteDataDirConfig(const DataDir: String);
var
  Lines: TArrayOfString;
  Path: String;
begin
  Path := ConfigPath();
  if FileExists(Path) then
    Exit;
  ForceDirectories(DataDir);
  ForceDirectories(DataDir + '\images');
  ForceDirectories(DataDir + '\config');
  SetArrayLength(Lines, 3);
  Lines[0] := '{';
  Lines[1] := '  "data_dir": "' + JsonEscapePath(DataDir) + '"';
  Lines[2] := '}';
  SaveStringsToUTF8File(Path, Lines, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep <> ssPostInstall then
    Exit;
  { Silent update from the app must not rewrite the library path. }
  if WizardSilent then
    Exit;
  if DataDirPage <> nil then
    WriteDataDirConfig(DataDirPage.Values[0]);
end;

[Setup]
AppName=PortoWrite
AppVersion=0.9.1 Beta
AppId={{A3F2C1D8-7E4B-4A9F-B6C3-2D5E8F1A0B7C}
AppPublisher=portoWlabs
AppPublisherURL=https://ko-fi.com/portowlabs
AppSupportURL=mailto:portowlabs@gmail.com
DefaultDirName={autopf}\PortoWrite
DefaultGroupName=PortoWrite
OutputBaseFilename=PortoWrite-setup
OutputDir=Output
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableWelcomePage=no
; Portable installs skip the uninstaller registry entry
CreateUninstallRegKey=not IsPortable
Uninstallable=not IsPortable

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "standard"; Description: "Standard Installation (Program Files + Start Menu)"
Name: "portable"; Description: "Portable Installation (choose any folder, no shortcuts)"

[Components]
Name: "main"; Description: "PortoWrite Application"; Types: standard portable; Flags: fixed

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Types: standard

[Files]
Source: "dist\PortoWrite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

[Icons]
; Standard only: Start Menu and optional desktop shortcut
Name: "{group}\PortoWrite"; Filename: "{app}\PortoWrite.exe"; Check: not IsPortable
Name: "{group}\{cm:UninstallProgram,PortoWrite}"; Filename: "{uninstallexe}"; Check: not IsPortable
Name: "{autodesktop}\PortoWrite"; Filename: "{app}\PortoWrite.exe"; Tasks: desktopicon; Check: not IsPortable

[Run]
Filename: "{app}\PortoWrite.exe"; Description: "{cm:LaunchProgram,PortoWrite}"; Flags: nowait postinstall skipifsilent

[Code]
function IsPortable: Boolean;
begin
  Result := WizardSetupType(False) = 'portable';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if IsPortable then
    begin
      { Portable: write a marker file so the app knows it's portable mode }
      SaveStringToFile(ExpandConstant('{app}\portable.marker'), '', False);
    end;
  end;
end;

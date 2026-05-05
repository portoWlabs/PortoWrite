; PortoWrite — Inno Setup installer script
; Compile with: ISCC.exe installer.iss
; Requires: Inno Setup 6+ from https://jrsoftware.org/isdl.php
; Requires: PyInstaller dist folder at dist\PortoWrite\

#define AppName "PortoWrite"
#define AppVersion "0.9.0 Beta"
#define AppPublisher "PortoWlabs"
#define AppURL "https://github.com/portoWlabs/PortoWrite"
#define AppExeName "PortoWrite.exe"
#define AppContact "portowlabs@gmail.com"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppContact={#AppContact}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=PortoWrite-{#AppVersion}-setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
InfoBeforeFile=README_install.txt
SetupIconFile=portowrite.ico
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application folder (PyInstaller dist output)
Source: "dist\PortoWrite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any user-created temp files in the app directory on uninstall
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    MsgBox(
      'Thank you for trying PortoWrite!' + #13#10 + #13#10 +
      'PortoWrite is free during the beta period.' + #13#10 +
      'If you find it useful, consider supporting development' + #13#10 +
      'via Ko-fi — it keeps the project alive.' + #13#10 + #13#10 +
      'Contact: portowlabs@gmail.com',
      mbInformation, MB_OK);
end;

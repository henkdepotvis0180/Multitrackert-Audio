#define AppVersion GetEnv("MULTITRACK_BUILD_VERSION")
#if AppVersion == ""
  #error MULTITRACK_BUILD_VERSION is required
#endif
[Setup]
AppId={{59AEF100-0D72-4B76-A1B6-72915B914D0C}
AppName=Multitrackert Audio
AppVersion={#AppVersion}
AppPublisher=Multitrackert Audio contributors
AppPublisherURL=https://github.com/henkdepotvis0180/Multitrackert-Audio
DefaultDirName={autopf}\Multitrackert Audio
DefaultGroupName=Multitrackert Audio
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
DisableDirPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=admin
OutputDir=..\artifacts
OutputBaseFilename=Multitrackert-Audio-Setup-{#AppVersion}-CPU-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
InfoBeforeFile=installer-info.txt
UninstallDisplayIcon={app}\MultitrackertAudio.exe
CloseApplications=yes
RestartApplications=no
[Tasks]
Name: desktopicon; Description: "Snelkoppeling op het bureaublad"; Flags: unchecked
[InstallDelete]
; Only old program binaries, NEVER the user's external project directories.
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\MultitrackertAudio.exe"
[Files]
Source: "..\dist\MultitrackertAudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
[Icons]
Name: "{group}\Multitrackert Audio"; Filename: "{app}\MultitrackertAudio.exe"
Name: "{autodesktop}\Multitrackert Audio"; Filename: "{app}\MultitrackertAudio.exe"; Tasks: desktopicon
[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Microsoft C++ runtime installeren..."; Flags: waituntilterminated; Check: NeedsVCRuntime
Filename: "{app}\MultitrackertAudio.exe"; Description: "Multitrackert Audio starten"; Flags: nowait postinstall skipifsilent runasoriginaluser
[Code]
function NeedsVCRuntime: Boolean;
var Installed, Minor: Cardinal;
begin
  Result := not (RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) and (Installed = 1) and RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Minor', Minor) and (Minor >= 44));
end;
function StopExistingApp: Boolean;
var Code, I: Integer;
begin
  Result := True;
  if CheckForMutexes('Local\MultitrackertAudioServer') then begin
    if FileExists(ExpandConstant('{app}\MultitrackertAudio.exe')) then
      Exec(ExpandConstant('{app}\MultitrackertAudio.exe'), '--quit', '', SW_HIDE, ewWaitUntilTerminated, Code);
    for I := 1 to 30 do begin
      if not CheckForMutexes('Local\MultitrackertAudioServer') then Exit;
      Sleep(500);
    end;
    Result := not CheckForMutexes('Local\MultitrackertAudioServer');
  end;
end;
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not StopExistingApp then
    Result := 'Sluit Multitrackert Audio via de knop App afsluiten en probeer opnieuw. Je projectbestanden blijven bewaard.';
end;
function InitializeUninstall: Boolean;
begin
  Result := StopExistingApp;
  if not Result then
    MsgBox('Sluit eerst Multitrackert Audio. Bewaarde projecten worden niet verwijderd door de uninstaller.', mbInformation, MB_OK);
end;

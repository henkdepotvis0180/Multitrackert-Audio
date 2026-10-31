param([Parameter(Mandatory=$true)][string]$Installer)
$ErrorActionPreference = 'Stop'
trap {
    $message = $_.Exception.Message.Replace('%','%25').Replace("`r",'%0D').Replace("`n",'%0A')
    Write-Output "::error title=Windows installer verification::$message"
    if (Test-Path $InstallLog) {
        $tail = (Get-Content $InstallLog -Tail 35) -join "`n"
        Write-Output ("::error title=Installer log tail::" + $tail.Replace('%','%25').Replace("`r",'%0D').Replace("`n",'%0A'))
    }
    exit 1
}
$Installer = (Resolve-Path $Installer).Path
$InstallDir = Join-Path $env:LOCALAPPDATA 'Multitrackert-Installer-Test'
$DataDir = Join-Path $env:RUNNER_TEMP 'multitrack-installer-retained-data'
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$env:MULTITRACK_DATA = $DataDir
$env:MULTITRACK_NO_BROWSER = '1'
$InstallLog = Join-Path $env:RUNNER_TEMP 'multitrack-install.log'
# Stable AppId and explicit binary cleanup are exercised by installing twice.
foreach ($n in 1..2) {
    Write-Output "::notice title=Installer progress::Installation pass $n started"
    $process = Start-Process -FilePath $Installer -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=`"$InstallDir`" /LOG=`"$InstallLog`"" -PassThru -Wait
    if ($process.ExitCode -notin @(0,3010)) { throw "Installer failed with exit $($process.ExitCode); $InstallLog" }
    if (-not (Test-Path "$InstallDir\MultitrackertAudio.exe")) { throw 'Installed executable missing' }
    Write-Output "::notice title=Installer progress::Installation pass $n completed; testing installed app"
    python windows/smoke_test.py "$InstallDir\MultitrackertAudio.exe"
    if ($LASTEXITCODE -ne 0) { throw 'Installed app smoke test failed' }
    if ($n -eq 1) {
        $savedProjects = Get-ChildItem $DataDir -Recurse -File | Where-Object { $_.Extension -in @('.wav','.mp4') -or $_.Name -eq 'result.zip' } | ForEach-Object {
            @{ Path = $_.FullName; Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash }
        }
        if (-not $savedProjects) { throw 'No generated export to test retention' }
        Set-Content -Path (Join-Path $DataDir 'retained-audio.wav') -Value 'user audio retention sentinel'
        Set-Content -Path "$InstallDir\_internal\old-version-only.txt" -Value 'stale program file'
        # Exercise the actual shutdown path during upgrade, not only an idle reinstall.
        $oldProcess = Start-Process -FilePath "$InstallDir\MultitrackertAudio.exe" -PassThru
        $ready = $false
        foreach ($attempt in 1..120) {
            try {
                $health = Invoke-RestMethod http://127.0.0.1:8765/api/health
                if ($health.desktop) { $ready = $true; break }
            } catch { Start-Sleep -Milliseconds 500 }
        }
        if (-not $ready) { throw 'Could not start the old app before upgrade' }
    }
}
if (-not $oldProcess.HasExited) { throw 'Installer did not stop the old running app' }
if (Test-Path "$InstallDir\_internal\old-version-only.txt") { throw 'Old program files were not replaced' }
if (-not (Test-Path (Join-Path $DataDir 'retained-audio.wav'))) { throw 'Update removed user data' }
foreach ($saved in $savedProjects) {
    if ((Get-FileHash $saved.Path -Algorithm SHA256).Hash -ne $saved.Hash) { throw "Update modified a saved ZIP" }
}
Write-Output "::notice title=Installer progress::Upgrade and retained media verified; checking uninstall"
$Uninstaller = Join-Path $InstallDir 'unins000.exe'
$process = Start-Process -FilePath $Uninstaller -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Uninstall failed with $($process.ExitCode)" }
if (-not (Test-Path (Join-Path $DataDir 'retained-audio.wav'))) { throw 'Uninstall removed user data' }
foreach ($saved in $savedProjects) {
    if ((Get-FileHash $saved.Path -Algorithm SHA256).Hash -ne $saved.Hash) { throw "Uninstall removed a saved export" }
}
Write-Output 'Installer, update, stale-file removal, frozen app and preserved user data: OK'

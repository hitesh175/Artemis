param(
    [string]$Target=(Join-Path $env:LOCALAPPDATA 'Artemis'),
    [string]$PythonPath,
    [switch]$CheckOnly,
    [switch]$Resume,
    [switch]$Yes,
    [switch]$NoShortcuts,
    [switch]$DesktopShortcut
)
$ErrorActionPreference='Stop'
$releaseRoot=Split-Path $PSScriptRoot -Parent
if (-not (Test-Path -LiteralPath (Join-Path $releaseRoot 'MANIFEST.json'))) { throw 'Extract the complete Artemis source ZIP, then run this installer from its scripts folder.' }
$candidates=@()
if ($PythonPath) { $candidates+=@{exe=$PythonPath;prefix=@()} }
else {
    $py=Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { $candidates+=@{exe=$py.Source;prefix=@('-3.11')} }
    $python=Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { $candidates+=@{exe=$python.Source;prefix=@()} }
}
$selected=$null
foreach ($candidate in $candidates) {
    try {
        $candidateExe=$candidate.exe
        $candidatePrefix=@($candidate.prefix)
        $probe=& $candidateExe @candidatePrefix -c "import sys,struct; print('ARTEMIS_PY_OK' if sys.version_info[:2]==(3,11) and struct.calcsize('P')==8 else 'UNSUPPORTED')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $probe -eq 'ARTEMIS_PY_OK') { $selected=$candidate;break }
    } catch { continue }
}
if (-not $selected) { throw 'Install Python 3.11 x64 from https://www.python.org/downloads/windows/ and run setup again.' }
$targetRoot=[IO.Path]::GetFullPath($Target)
$selectedExe=$selected.exe
$engine=Join-Path $PSScriptRoot 'windows_setup.py'
$arguments=@($selected.prefix)+@($engine,'--source-root',$releaseRoot,'--target',$targetRoot)
Write-Host 'Artemis guided Windows setup'
Write-Host ('Destination: '+$targetRoot)
Write-Host 'Existing installations are kept. Application packages may be downloaded; model downloads are separate.'
if ($CheckOnly) {
    & $selectedExe @arguments --check
    if ($LASTEXITCODE -ne 0) { throw 'Prerequisite or release checks failed.' }
    exit 0
}
if (-not $Yes) {
    $answer=Read-Host 'Install into this new folder? Type Install to continue'
    if ($answer -ne 'Install') { Write-Host 'Setup cancelled.';exit 0 }
}
if ($Resume) { $arguments+='--resume' }
& $selectedExe @arguments
if ($LASTEXITCODE -ne 0) { throw 'Setup did not complete. See artemis-setup.json in the destination and FIRST_RUN.md in the release setup folder.' }
if (-not $NoShortcuts) {
    $shell=New-Object -ComObject WScript.Shell
    $links=@((Join-Path $targetRoot 'Artemis.lnk'))
    $menu=Join-Path ([Environment]::GetFolderPath('Programs')) 'Artemis'
    New-Item -ItemType Directory -Force -Path $menu | Out-Null
    $links+=Join-Path $menu 'Artemis.lnk'
    if ($DesktopShortcut) { $links+=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Artemis.lnk' }
    foreach ($link in $links) {
        if (Test-Path -LiteralPath $link) { Write-Host ('Existing shortcut kept: '+$link);continue }
        $shortcut=$shell.CreateShortcut($link)
        $shortcut.TargetPath=Join-Path $targetRoot '.venv\Scripts\pythonw.exe'
        $shortcut.Arguments='"'+(Join-Path $targetRoot 'Artemis.pyw')+'"'
        $shortcut.WorkingDirectory=$targetRoot
        $shortcut.IconLocation=Join-Path $targetRoot 'desktop\assets\Artemis.ico'
        $shortcut.Save()
    }
}
Write-Host ('Setup complete. Read '+(Join-Path $targetRoot 'FIRST_RUN.md'))
Write-Host 'No model downloads, microphone capture, speech, autostart or schedules were enabled.'

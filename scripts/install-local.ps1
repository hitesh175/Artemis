param([string]$Target='C:\Users\kanag\Desktop\Artemis')
$ErrorActionPreference='Stop'
$workspace=Split-Path $PSScriptRoot -Parent
$source=Join-Path $workspace 'app'
$targetRoot=[IO.Path]::GetFullPath($Target).TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $targetRoot 'Artemis.exe'))) { throw 'Existing Artemis installation was not found.' }
$running=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(pythonw?|Artemis)\.exe$' -and $_.CommandLine -like "*$targetRoot*" }
if ($running) { throw 'Close Artemis before installing.' }
$files=Get-ChildItem -LiteralPath $source -Recurse -File | Where-Object { $_.FullName -notmatch '\\(__pycache__|data|logs|models|voice_test|\.venv)\\' -and $_.Extension -ne '.pyc' }
$backup=Join-Path $targetRoot ('ui-backups\before-integrated-features-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$records=@()
foreach ($file in $files) {
    $relative=$file.FullName.Substring($source.Length+1)
    $destination=[IO.Path]::GetFullPath((Join-Path $targetRoot $relative))
    if (-not $destination.StartsWith($targetRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escaped installation.' }
    $existed=Test-Path -LiteralPath $destination -PathType Leaf
    if ($existed) {
        $saved=Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $saved) | Out-Null
        Copy-Item -LiteralPath $destination -Destination $saved
    }
    $records+=@{path=$relative;existed=$existed;sha256=(Get-FileHash -LiteralPath $file.FullName).Hash}
}
@{target=$targetRoot;files=$records;dependency='pypdf==6.10.0';dependencyPreviouslyAbsent=$true} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $backup 'install-manifest.json')
$python=Join-Path $targetRoot '.venv\Scripts\python.exe'
& $python -m pip install 'pypdf==6.10.0'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; application files were not replaced.' }
foreach ($file in $files) {
    $relative=$file.FullName.Substring($source.Length+1)
    $destination=Join-Path $targetRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    if ((Get-FileHash -LiteralPath $destination).Hash -ne (Get-FileHash -LiteralPath $file.FullName).Hash) { throw "Copy verification failed: $relative" }
}
Write-Output "INSTALLED: $($files.Count) files verified"
Write-Output "BACKUP: $backup"

param([Parameter(Mandatory=$true)][string]$Backup)
$ErrorActionPreference='Stop'
$backupRoot=(Resolve-Path -LiteralPath $Backup).Path
$manifest=Get-Content -LiteralPath (Join-Path $backupRoot 'install-manifest.json') -Raw | ConvertFrom-Json
$targetRoot=[IO.Path]::GetFullPath($manifest.target).TrimEnd('\')
if (-not $backupRoot.StartsWith($targetRoot+'\ui-backups\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Backup is outside the installation backup directory.' }
$running=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(pythonw?|Artemis)\.exe$' -and $_.CommandLine -like "*$targetRoot*" }
if ($running) { throw 'Close Artemis before rollback.' }
foreach ($entry in $manifest.files) {
    $destination=[IO.Path]::GetFullPath((Join-Path $targetRoot $entry.path))
    $saved=[IO.Path]::GetFullPath((Join-Path $backupRoot $entry.path))
    if (-not $destination.StartsWith($targetRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or -not $saved.StartsWith($backupRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe backup path.' }
    if ($entry.existed) { Copy-Item -LiteralPath $saved -Destination $destination -Force }
    elseif (Test-Path -LiteralPath $destination -PathType Leaf) {
        if ((Get-FileHash -LiteralPath $destination).Hash -ne $entry.sha256) { throw 'A newly installed file has changed; preserve it before rollback.' }
        Remove-Item -LiteralPath $destination
    }
}
Write-Output 'Application files restored. User data and models were preserved. The compatible pypdf package is retained.'

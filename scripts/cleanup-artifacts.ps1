param(
    [switch]$Apply,
    [switch]$IncludeInstalledBackups,
    [string]$InstalledRoot='C:\Users\kanag\Desktop\Artemis'
)
$ErrorActionPreference='Stop'
$workspace=[IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$installed=[IO.Path]::GetFullPath($InstalledRoot).TrimEnd('\')
$targets=@()
$historical=@('Artemis-Antimatter','Artemis-App','Artemis-App-Routing','Artemis-Apps',
    'Artemis-Branding','Artemis-Cosmic','Artemis-Daily','Artemis-Executable','Artemis-Handsfree',
    'Artemis-Icon','Artemis-Mini','Artemis-Music','Artemis-Music-Guest','Artemis-Quiet',
    'Artemis-Reactive','Artemis-Recovery','Artemis-Redesign','Artemis-Silver','Artemis-Stability',
    'Artemis-Voice-Fix','Artemis-Weather-Intent','Artemis-Weather-Routing','Artemis-YouTube','baseline',
    'Artemis-A-Emblem-UI.zip','Artemis-Animated-Icon-UI.zip','Artemis-Antimatter-Update.zip',
    'Artemis-App-Launching-Update.zip','Artemis-Atelier-UI.zip','Artemis-Borderless-App-Update.zip',
    'Artemis-Brave-Guest-Music.zip','Artemis-Core-Update.zip','Artemis-Cosmic-UI.zip',
    'Artemis-Everyday-Update.zip','Artemis-Executable-Update.zip','Artemis-Handsfree-Update.zip',
    'Artemis-Lunar-Update.zip','Artemis-Mini-Update.zip','Artemis-Premium-UI.zip',
    'Artemis-Quiet-Saved-Chats.zip','Artemis-Reactive-Icon-Update.zip','Artemis-Silver-UI.zip',
    'output\installer-app-qa','output\installer-app-qa2','output\installer-source-qa','output\installer-source-qa2')
foreach($relative in $historical){
    $candidate=Join-Path $workspace $relative
    if(Test-Path -LiteralPath $candidate){$targets+=@{path=$candidate;root=$workspace;kind='historical build or installer test'}}
}
$keptBackup=$null
if($IncludeInstalledBackups){
    $backupRoot=Join-Path $installed 'ui-backups'
    if(Test-Path -LiteralPath $backupRoot){
        $backups=@(Get-ChildItem -LiteralPath $backupRoot -Directory | Where-Object Name -Like 'before-*' | Sort-Object LastWriteTime -Descending)
        if($backups.Count -gt 0){$keptBackup=$backups[0].FullName}
        foreach($backup in ($backups | Select-Object -Skip 1)){
            $targets+=@{path=$backup.FullName;root=$backupRoot;kind='superseded UI backup'}
        }
    }
}
$records=@()
foreach($target in $targets){
    $allowed=[IO.Path]::GetFullPath($target.root).TrimEnd('\')
    $resolved=(Resolve-Path -LiteralPath $target.path).ProviderPath
    if(-not $resolved.StartsWith($allowed+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Cleanup target escaped the allowed directory.'}
    $item=Get-Item -LiteralPath $resolved -Force
    if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw ('Linked target requires separate review: '+$resolved)}
    $children=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $resolved -Recurse -Force)}else{@($item)}
    if($children | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }){throw ('Linked content requires separate review: '+$resolved)}
    $bytes=[long](($children | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum)
    $records+=@{path=$resolved;bytes=$bytes;kind=$target.kind;removed=$false}
}
$report=@{applied=[bool]$Apply;keptBackup=$keptBackup;bytesRemoved=0;targets=$records}
$reportFolder=Join-Path $workspace 'output'
New-Item -ItemType Directory -Force -Path $reportFolder | Out-Null
$reportFile=Join-Path $reportFolder 'cleanup-report.json'
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportFile -Encoding utf8
if($Apply){
    foreach($record in $records){
        Remove-Item -LiteralPath $record.path -Recurse -Force
        $record.removed=$true
        $report.bytesRemoved+=$record.bytes
        $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportFile -Encoding utf8
    }
}
[pscustomobject]@{Applied=[bool]$Apply;Targets=$records.Count;MB=[math]::Round((($records | Measure-Object bytes -Sum).Sum)/1MB,2);KeptBackup=$keptBackup;Report=$reportFile} | Format-List

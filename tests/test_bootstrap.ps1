# No Pester, network, system installs, or application launches required.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
. (Join-Path $root 'install.ps1')
function Assert($Condition,[string]$Message) { if (-not $Condition) { throw $Message } }
$tokens=$null;$parseErrors=$null
foreach ($file in @((Join-Path $root 'install.ps1'),(Join-Path $root 'scripts\install-windows.ps1'))) {
    [System.Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$parseErrors) | Out-Null
    Assert ($parseErrors.Count -eq 0) "Invalid PowerShell: $file $parseErrors"
}
$script:requests=0
function Invoke-WebRequest { param([switch]$UseBasicParsing,$Uri,$OutFile,$TimeoutSec) $script:requests++;throw 'simulated interruption' }
try { Get-ArtemisDownload 'https://example.test/file' 'unused' ;throw 'Expected failure' }
catch { Assert ($_.Exception.Message -eq 'simulated interruption') 'Download failure was not propagated.' }
Assert ($script:requests -eq 3) 'Network retries are not bounded.'
try { Get-ArtemisDownload 'http://example.test/file' 'unused';throw 'Expected failure' }
catch { Assert ($_.Exception.Message -match 'HTTPS') 'Insecure URL was accepted.' }
$script:started=$false
function Get-ArtemisDownload {}
function Get-AuthenticodeSignature { return @{Status='NotSigned'} }
function Start-Process { $script:started=$true }
try { Install-ArtemisSignedTool 'https://example.test/file' 'unused' '/silent';throw 'Expected failure' }
catch { Assert ($_.Exception.Message -match 'trusted signature') 'Unsigned executable was accepted.' }
Assert (-not $script:started) 'Untrusted installer was started.'
# Existing unmarked destinations must fail before any network or system work.
$Target=$root
$Yes=$true
try { Start-ArtemisSetup;throw 'Expected failure' }
catch { Assert ($_.Exception.Message -match 'already exists') 'Existing source folder was not protected.' }
Write-Output 'PASS: bootstrap syntax, bounded retries, HTTPS, executable trust, existing-folder protection'

# Exercise the real orchestrator with fake external boundaries. No tools installed.
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('ArtemisBootstrapTest-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture | Out-Null
$previousLocal=$env:LOCALAPPDATA
try {
    $env:LOCALAPPDATA=$fixture
    $Target=Join-Path $fixture 'installed'
    $Revision='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    $NoLaunch=$true
    $TextOnly=$false
    $script:failModels=$true
    $script:launches=0
    $script:calls=@()
    function Test-PythonProbe { 'READY' }
    function Get-ArtemisPython { 'Test-PythonProbe' }
    function Find-ArtemisOllama { 'fake-ollama.exe' }
    function Test-ArtemisOllama { $true }
    function Expand-Archive {
        param($LiteralPath,$DestinationPath)
        New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
        if ((Split-Path $DestinationPath -Leaf) -eq 'release') {
            Set-Content -LiteralPath (Join-Path $DestinationPath 'MANIFEST.json') -Value '{}' -Encoding UTF8
        }
    }
    function Start-Process { $script:launches++ }
    function Invoke-ArtemisCommand {
        param($Exe,$Arguments)
        $script:calls+=,@($Arguments)
        if ($Arguments -contains '-File') {
            $releasePath=Split-Path (Split-Path $Arguments[4] -Parent) -Parent
            New-Item -ItemType Directory -Path $Target -Force | Out-Null
            @{state='complete';release=(Get-FileHash -LiteralPath (Join-Path $releasePath 'MANIFEST.json')).Hash} |
                ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Target 'artemis-setup.json') -Encoding UTF8
        }
        if (($Arguments[0] -like '*prepare-models.py') -and $script:failModels) { throw 'simulated model failure' }
    }
    # PowerShell native success codes remain visible through mock commands.
    $global:LASTEXITCODE=0
    try { Start-ArtemisSetup;throw 'Expected failure' }
    catch { Assert ($_.Exception.Message -eq 'simulated model failure') "Unexpected setup failure: $_" }
    Assert ($script:launches -eq 0) 'App launched after model preparation failed.'
    Assert (Test-Path -LiteralPath (Join-Path $Target 'artemis-setup.json')) 'Recovery marker was not retained.'
    $script:failModels=$false
    $TextOnly=$true
    Start-ArtemisSetup
    Assert ($script:launches -eq 0) '-NoLaunch was ignored.'
    Assert ($script:calls[-2] -contains '-ShortcutsOnly') 'Completed package setup was reinstalled.'
    Assert ($script:calls[-1] -contains '--text-only') 'Text-only selection did not reach model setup.'
    $NoLaunch=$false
    $TextOnly=$false
    Start-ArtemisSetup
    Assert ($script:launches -eq 1) 'App was not launched after successful full setup.'
    Assert (-not ($script:calls[-1] -contains '--text-only')) 'Default setup skipped voice.'
    $Revision='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
    try { Start-ArtemisSetup;throw 'Expected failure' }
    catch { Assert ($_.Exception.Message -match 'different revision') 'Mixed-release recovery was accepted.' }
    Write-Output 'PASS: full orchestration, interrupted model recovery, package reuse, text-only/full routing, launch guards, revision pinning'
} finally {
    $env:LOCALAPPDATA=$previousLocal
    $resolved=[IO.Path]::GetFullPath($fixture)
    $testTemp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if ($resolved.StartsWith($testTemp,[StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf) -match '^ArtemisBootstrapTest-[a-f0-9]{32}$') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

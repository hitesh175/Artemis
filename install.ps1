# Artemis online setup. Independently implemented; no OpenJarvis code is used.
[CmdletBinding()]
param(
    [string]$Target=(Join-Path $env:LOCALAPPDATA 'Artemis'),
    [ValidatePattern('^[a-fA-F0-9]{40}$')][string]$Revision,
    [switch]$TextOnly,
    [switch]$NoLaunch,
    [switch]$Yes,
    [switch]$CheckOnly
)

function Get-ArtemisDownload([string]$Url,[string]$Path) {
    if (-not $Url.StartsWith('https://')) { throw 'Setup downloads require HTTPS.' }
    for ($attempt=1;$attempt -le 3;$attempt++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile ($Path+'.partial') -TimeoutSec 180
            Move-Item -LiteralPath ($Path+'.partial') -Destination $Path -Force
            return
        } catch {
            if ($attempt -eq 3) { throw }
            Write-Host "Download interrupted; retrying ($attempt/3)..."
        }
    }
}

function Invoke-ArtemisCommand([string]$Exe,[string[]]$Arguments) {
    & $Exe @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Setup step failed ($LASTEXITCODE): $Exe" }
}

function Install-ArtemisSignedTool([string]$Url,[string]$Path,[string]$Arguments) {
    Get-ArtemisDownload $Url $Path
    $signature=Get-AuthenticodeSignature -LiteralPath $Path
    if ($signature.Status -ne 'Valid') { throw "The downloaded installer has no valid trusted signature: $Path" }
    $process=Start-Process -FilePath $Path -ArgumentList $Arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -notin @(0,3010)) { throw "Requirement installation failed ($($process.ExitCode))." }
}

function Find-ArtemisPython {
    $candidates=@()
    $launcher=Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        try { $candidates+=(& $launcher.Source -3.11 -c 'import sys; print(sys.executable)' 2>$null) } catch {}
    }
    $command=Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates+=$command.Source }
    $candidates+=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    foreach ($candidate in $candidates) {
        if (-not $candidate -or -not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            $probe=& $candidate -c "import sys,struct; print('ARTEMIS_OK' if sys.version_info[:2]==(3,11) and struct.calcsize('P')==8 else '')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $probe -eq 'ARTEMIS_OK') { return [string]$candidate }
        } catch {}
    }
    return $null
}

function Get-ArtemisPython([string]$Work) {
    $python=Find-ArtemisPython
    if ($python) { return $python }
    Write-Host 'Preparing Python 3.11 with Astral uv...'
    $release=Invoke-RestMethod -Uri 'https://api.github.com/repos/astral-sh/uv/releases/latest'
    $asset='uv-x86_64-pc-windows-msvc.zip'
    $archive=Join-Path $Work $asset
    $base='https://github.com/astral-sh/uv/releases/download/'+$release.tag_name+'/'
    Get-ArtemisDownload ($base+$asset) $archive
    $checksum=Join-Path $Work 'uv.sha256'
    Get-ArtemisDownload ($base+$asset+'.sha256') $checksum
    $expected=((Get-Content -LiteralPath $checksum -Raw).Trim() -split '\s+')[0]
    if ($expected -notmatch '^[a-fA-F0-9]{64}$' -or (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expected) {
        throw 'Python manager download checksum did not match.'
    }
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $Work 'uv')
    $uv=(Get-ChildItem -LiteralPath (Join-Path $Work 'uv') -Filter uv.exe -Recurse -File | Select-Object -First 1).FullName
    if (-not $uv) { throw 'Python manager executable was not found.' }
    Invoke-ArtemisCommand $uv @('python','install','3.11','--no-bin','--no-registry','--no-config')
    $python=& $uv python find --managed-python --no-config 3.11
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $python)) { throw 'Python installation was not found.' }
    return [string]$python
}

function Find-ArtemisOllama {
    $command=Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $path=Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (Test-Path -LiteralPath $path -PathType Leaf) { return $path }
    return $null
}

function Test-ArtemisOllama {
    try {
        $reply=Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3
        return ($null -ne $reply.PSObject.Properties['models'])
    } catch { return $false }
}

function Start-ArtemisSetup {
    $ErrorActionPreference='Stop'
    [Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
        throw 'Open 64-bit PowerShell on Windows x64 to install Artemis.'
    }
    $targetRoot=[IO.Path]::GetFullPath($Target).TrimEnd('\')
    $marker=Join-Path $targetRoot 'artemis-setup.json'
    if ((Test-Path -LiteralPath $targetRoot) -and -not (Test-Path -LiteralPath $marker -PathType Leaf)) {
        throw 'This folder already exists and is not a guided installation. Choose a new -Target; existing apps are kept.'
    }
    Write-Host 'Artemis complete Windows setup'
    Write-Host "Destination: $targetRoot"
    Write-Host 'Installs missing Python, WebView2 and Ollama; downloads the Artemis chat model.'
    if (-not $TextOnly) { Write-Host 'Also prepares Whisper recognition and Kokoro speech models.' }
    Write-Host 'Allow several GB of downloads and at least 12 GB free on your system drive.'
    Write-Host 'Quiet mode starts on. Setup does not record or play audio.'
    if ($CheckOnly) {
        Write-Host ('Python available: '+[bool](Find-ArtemisPython))
        Write-Host ('Ollama available: '+[bool](Find-ArtemisOllama))
        Write-Host 'Check only: nothing downloaded or installed.'
        return
    }
    if (-not $Yes -and (Read-Host 'Continue with downloads and setup? [Y/n]') -notin @('','y','Y','yes','Yes')) { return }
    $cache=Join-Path $env:LOCALAPPDATA 'ArtemisSetup'
    New-Item -ItemType Directory -Path $cache -Force | Out-Null
    $hasher=[Security.Cryptography.SHA256]::Create()
    try { $key=([BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($targetRoot.ToLowerInvariant())))).Replace('-','') }
    finally { $hasher.Dispose() }
    $receipt=Join-Path $cache ($key+'.json')
    $commit=$Revision
    if (Test-Path -LiteralPath $receipt) {
        $saved=Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
        if ($commit -and $commit -ne $saved.revision) { throw 'Use a new destination for a different revision.' }
        $commit=$saved.revision
    }
    if (-not $commit) { $commit=(Invoke-RestMethod 'https://api.github.com/repos/hitesh175/Artemis/commits/main').sha }
    if ($commit -notmatch '^[a-fA-F0-9]{40}$') { throw 'Invalid source revision.' }
    @{revision=$commit;target=$targetRoot} | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding UTF8
    $work=Join-Path ([IO.Path]::GetTempPath()) ('ArtemisSetup-'+[Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $work | Out-Null
    try {
        Write-Host '[1/5] Preparing Python and application source...'
        $python=Get-ArtemisPython $work
        $zip=Join-Path $work 'source.zip'
        Get-ArtemisDownload "https://github.com/hitesh175/Artemis/archive/$commit.zip" $zip
        Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $work 'source')
        $source=Join-Path $work "source\Artemis-$commit"
        Invoke-ArtemisCommand $python @((Join-Path $source 'scripts\build.py'))
        $release=Join-Path $work 'release'
        Expand-Archive -LiteralPath (Join-Path $source 'output\releases\artemis-source.zip') -DestinationPath $release
        Write-Host '[2/5] Checking the desktop runtime...'
        $probe=& $python -c "import sys;sys.path.insert(0,sys.argv[1]);from windows_setup import webview_runtime;print('READY' if webview_runtime() else 'MISSING')" (Join-Path $release 'scripts')
        if ($LASTEXITCODE -ne 0) { throw 'Desktop runtime check failed.' }
        if ($probe -ne 'READY') {
            Install-ArtemisSignedTool 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' (Join-Path $work 'WebView2.exe') '/silent /install'
        }
        Write-Host '[3/5] Installing Artemis and its packages...'
        $resume=$false
        $complete=$false
        if (Test-Path -LiteralPath $marker) {
            $status=Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
            $manifestHash=(Get-FileHash -LiteralPath (Join-Path $release 'MANIFEST.json') -Algorithm SHA256).Hash
            if ($status.release -ne $manifestHash) { throw 'This destination belongs to another release. Choose a new folder.' }
            $complete=$status.state -eq 'complete'
            $resume=-not $complete
        }
        $installerArguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $release 'scripts\install-windows.ps1'),'-Target',$targetRoot,'-PythonPath',$python,'-Yes','-DesktopShortcut')
        if ($complete) { $installerArguments+='-ShortcutsOnly' }
        elseif ($resume) { $installerArguments+='-Resume' }
        Invoke-ArtemisCommand (Get-Command powershell.exe -ErrorAction Stop).Source $installerArguments
        Write-Host '[4/5] Preparing Ollama...'
        $ollama=Find-ArtemisOllama
        if (-not $ollama) {
            Install-ArtemisSignedTool 'https://ollama.com/download/OllamaSetup.exe' (Join-Path $work 'OllamaSetup.exe') '/VERYSILENT /NORESTART /SUPPRESSMSGBOXES'
            $ollama=Find-ArtemisOllama
        }
        if (-not $ollama) { throw 'Ollama was not found after installation.' }
        if (-not (Test-ArtemisOllama)) {
            Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden | Out-Null
            for ($attempt=0;$attempt -lt 30 -and -not (Test-ArtemisOllama);$attempt++) { Start-Sleep -Seconds 2 }
        }
        if (-not (Test-ArtemisOllama)) { throw 'Ollama did not start. Start Ollama and rerun setup to continue.' }
        Write-Host '[5/5] Preparing models and checking readiness...'
        $installedPython=Join-Path $targetRoot '.venv\Scripts\python.exe'
        $arguments=@((Join-Path $targetRoot 'setup\prepare-models.py'),'--root',$targetRoot,'--ollama',$ollama)
        if ($TextOnly) { $arguments+='--text-only' }
        Invoke-ArtemisCommand $installedPython $arguments
        Write-Host 'Artemis is ready. Use the Artemis shortcut on your desktop or Start menu.'
        if (-not $NoLaunch) {
            Start-Process -FilePath (Join-Path $targetRoot '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+(Join-Path $targetRoot 'Artemis.pyw')+'"') -WorkingDirectory $targetRoot -WindowStyle Hidden | Out-Null
        }
    } finally {
        # Only this invocation's freshly created, verified temporary directory.
        $resolved=[IO.Path]::GetFullPath($work)
        $tempRoot=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
        if ($resolved.StartsWith($tempRoot,[StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf) -match '^ArtemisSetup-[a-f0-9]{32}$') {
            Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Start-ArtemisSetup }
    catch {
        Write-Host 'Setup did not finish. Rerun the same command and destination to retry; completed models are kept.'
        throw
    }
}

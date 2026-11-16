param([switch]$Check,[switch]$SkipInstall,[switch]$NoBrowser,[int]$Port=8501)
$ErrorActionPreference='Stop'
$projectPath=Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectPath 'scripts/windows_common.ps1')
Push-Location -LiteralPath $projectPath
try {
    if ($Port -lt 1 -or $Port -gt 65535) { throw 'Choose a port from 1 to 65535.' }
    $state=Get-VenvState $projectPath
    if ($state.Status -ne 'ready') { throw "$($state.Reason). Run SETUP_SHERLOCKED.bat. Setup preserves an old/moved environment before recreating it." }
    $python=$state.Python
    & $python -B scripts/health.py --lightweight
    if ($LASTEXITCODE -ne 0) { throw 'Startup checks failed. Run SETUP_SHERLOCKED.bat; START never installs dependencies or rewrites datasets.' }
    if ($Check) { Write-Host 'SHERLOCKED startup checks passed; no server was started.'; exit 0 }
    Write-Host "SHERLOCKED is starting at http://localhost:$Port"
    Write-Host 'Press Ctrl+C to stop. Active CPU/CUDA model state is shown in the application.'
    $launchArgs=@('--port', $Port)
    if ($NoBrowser) { $launchArgs+='--no-browser' }
    & $python (Join-Path $projectPath 'scripts/launch_app.py') @launchArgs
    if ($LASTEXITCODE -ne 0) { throw 'Streamlit failed; review the message above or try another -Port.' }
} catch {
    Write-Host "SHERLOCKED START: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally { Pop-Location }


param(
    [string]$PythonPath,
    [switch]$Cuda,
    [switch]$Cpu,
    [Alias('Online')][switch]$DownloadModel,
    [switch]$Offline,
    [switch]$SkipInstall,
    [switch]$RecreateEnvironment,
    [string]$Wheelhouse
)
function Get-TorchInstallArguments([string]$WantedVersion,[string]$PackageIndex,[string]$WheelDirectory) {
    if ($WantedVersion -notin @('2.6.0+cpu','2.6.0+cu124')) { throw 'Unsupported PyTorch profile requested.' }
    $arguments=@('-m','pip','install',('torch=='+$WantedVersion))
    if ($WheelDirectory) { $arguments+=@('--no-index','--find-links',$WheelDirectory) }
    else { $arguments+=@('--index-url',$PackageIndex) }
    return $arguments
}
$ErrorActionPreference='Stop'
$projectPath=Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectPath 'scripts/windows_common.ps1')
Push-Location -LiteralPath $projectPath
try {
    if ($Cuda -and $Cpu) { throw 'Choose -Cpu or -Cuda, not both.' }
    if ($DownloadModel -and $Offline) { throw 'Choose -DownloadModel or -Offline, not both.' }
    $state=Get-VenvState $projectPath
    $fresh=$state.Status -ne 'ready' -or $RecreateEnvironment
    if ($fresh) {
        $systemPython=Find-SupportedPython $PythonPath $state.Base
        if ($state.Status -ne 'missing') { Backup-Venv $projectPath }
        Write-Host 'Creating a project-local Python environment...'
        & $systemPython -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed; the previous environment was preserved under backups/environments.' }
    }
    $python=Join-Path $projectPath '.venv/Scripts/python.exe'
    & $python -B scripts/health.py --dependencies-only
    $needsInstall=$LASTEXITCODE -ne 0
    $torchVersion=& $python -B -c "import importlib.metadata as m; print(next((d.version for d in m.distributions() if d.metadata['Name'].lower()=='torch'),'missing'))"
    $wanted=$null
    if ($Cuda) { $wanted='2.6.0+cu124'; $index='https://download.pytorch.org/whl/cu124'; $profile='CUDA 12.4' }
    elseif ($Cpu -or $fresh -or $torchVersion -eq 'missing') { $wanted='2.6.0+cpu'; $index='https://download.pytorch.org/whl/cpu'; $profile='CPU' }
    $changeTorch=$wanted -and $torchVersion -ne $wanted
    if ($fresh -or $needsInstall -or $changeTorch) {
        if ($SkipInstall) { throw 'Dependency installation is required; rerun setup without -SkipInstall.' }
        if ($Offline -and -not $Wheelhouse) { throw 'Offline dependency setup requires a prepared wheelhouse (-Wheelhouse path), or an environment prepared online first.' }
        $pipArgs=@()
        if ($Wheelhouse) {
            if (-not (Test-Path -LiteralPath $Wheelhouse)) { throw 'Wheelhouse directory not found.' }
            $pipArgs=@('--no-index','--find-links',$Wheelhouse)
        }
        if ($changeTorch) {
            Write-Host "Installing the $profile PyTorch package; no GPU drivers will be changed."
            # Exact local-version pins are required: the public 2.6.0 pin can
            # accept an already installed opposite CPU/CUDA profile.
            $torchArguments=@(Get-TorchInstallArguments $wanted $index $Wheelhouse)
            & $python @torchArguments
            if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed. Check internet/wheelhouse access and Python version.' }
            $installedProfile=& $python -B -c "import importlib.metadata as m; print(m.version('torch'))"
            if ($LASTEXITCODE -ne 0 -or $installedProfile -ne $wanted) {
                throw "PyTorch profile verification failed: requested $wanted but observed $installedProfile."
            }
        }
        Write-Host 'Installing missing or incompatible Python dependencies...'
        $installFile='requirements.txt'
        $minor=& $python -B -c 'import sys; print(sys.version_info.minor)'
        if ($minor -eq '12') {
            $actualTorch=& $python -B -c "import importlib.metadata as m; print(m.version('torch'))"
            $candidateLock=if ($actualTorch -like '*+cu*') { 'requirements-cuda-lock.txt' } else { 'requirements-cpu-lock.txt' }
            if (Test-Path -LiteralPath $candidateLock) { $installFile=$candidateLock }
        }
        Write-Host "Using dependency specification: $installFile"
        & $python -m pip install @pipArgs -r $installFile
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Existing reports and results were preserved.' }
    } else { Write-Host 'Supported dependencies are present; no packages were reinstalled.' }
    & $python -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed; review package errors above.' }
    & $python -B scripts/health.py --initialize --verify-imports
    if ($LASTEXITCODE -ne 0) { throw 'Installation validation failed; follow the reported errors. Dataset/results were not overwritten.' }
    if ($DownloadModel) {
        Write-Host 'Preparing the approved multilingual model online; existing cached assets are reused...'
        & $python -B scripts/setup_model.py --device auto
        if ($LASTEXITCODE -ne 0) { throw 'Model setup failed. Explicit lexical methods remain available; retry or transfer approved assets offline.' }
    } else { Write-Host 'Model assets checked without network access. Use SETUP_SHERLOCKED.bat -DownloadModel if assets are missing.' }
    Write-EnvironmentMarker $projectPath $python
    Write-Host 'SHERLOCKED setup passed. Start with START_SHERLOCKED.bat'
} catch {
    Write-Host "SHERLOCKED SETUP: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally { Pop-Location }



function Get-PortableFileHash([string]$Path) {
    $algorithm=[System.Security.Cryptography.SHA256]::Create()
    $stream=[System.IO.File]::OpenRead($Path)
    try { return [System.BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','') }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}
# Shared Windows checks; no data, model or environment writes occur here.
function Get-PythonInfo([string]$Executable) {
    try {
        $output=& $Executable -B -c "import json,sys; print(json.dumps({'version':list(sys.version_info[:2]),'prefix':sys.prefix,'base':getattr(sys,'_base_executable',sys.executable)}))" 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $info=$output | ConvertFrom-Json
        if ($info.version[0] -ne 3 -or $info.version[1] -lt 10 -or $info.version[1] -gt 12) { return $null }
        return $info
    } catch { return $null }
}
function Get-VenvState([string]$Project) {
    $directory=Join-Path $Project '.venv'
    $python=Join-Path $directory 'Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $directory)) { return [pscustomobject]@{Status='missing';Python=$python;Base=$null;Reason='Local environment is missing'} }
    $info=Get-PythonInfo $python
    if (-not $info) { return [pscustomobject]@{Status='invalid';Python=$python;Base=$null;Reason='Environment Python cannot run or is outside supported 3.10-3.12'} }
    $marker=Join-Path $directory 'sherlocked-environment.json'
    if (Test-Path -LiteralPath $marker) {
        try {
            $saved=Get-Content -Raw -LiteralPath $marker | ConvertFrom-Json
            if ([IO.Path]::GetFullPath($saved.project_root).TrimEnd('\') -ine [IO.Path]::GetFullPath($Project).TrimEnd('\')) {
                return [pscustomobject]@{Status='moved';Python=$python;Base=$info.base;Reason='Environment belongs to another project location'}
            }
        } catch { return [pscustomobject]@{Status='invalid';Python=$python;Base=$info.base;Reason='Environment marker is unreadable'} }
    } else {
        $activation=Join-Path $directory 'Scripts/activate.bat'
        if (Test-Path -LiteralPath $activation) {
            foreach ($line in Get-Content -LiteralPath $activation) {
                if ($line -match '^set "?VIRTUAL_ENV=(.+?)"?$') {
                    $previous=$Matches[1].Trim('"')
                    if ([IO.Path]::GetFullPath($previous).TrimEnd('\') -ine [IO.Path]::GetFullPath($directory).TrimEnd('\')) {
                        return [pscustomobject]@{Status='moved';Python=$python;Base=$info.base;Reason='Legacy activation points to another directory'}
                    }
                }
            }
        }
    }
    return [pscustomobject]@{Status='ready';Python=$python;Base=$info.base;Reason='Supported environment is available'}
}
function Find-SupportedPython([string]$Requested,[string]$ExistingBase) {
    $candidates=@()
    if ($Requested) {
        if (-not (Test-Path -LiteralPath $Requested)) { throw "Python not found: $Requested" }
        if (-not (Get-PythonInfo $Requested)) { throw 'Choose usable Python 3.10, 3.11 or 3.12.' }
        return (Resolve-Path -LiteralPath $Requested).Path
    }
    if ($ExistingBase -and (Test-Path -LiteralPath $ExistingBase)) { $candidates+=$ExistingBase }
    $launcher=Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($version in @('-3.12','-3.11','-3.10')) {
            try {
                $found=& $launcher.Source $version -c 'import sys; print(sys.executable)' 2>$null
                if ($LASTEXITCODE -eq 0) { $candidates+=$found }
            } catch { }
        }
    }
    foreach ($name in @('python.exe','python3.exe')) {
        $command=Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*WindowsApps*') { $candidates+=$command.Source }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) { if (Get-PythonInfo $candidate) { return $candidate } }
    throw 'Install Python 3.12 from python.org with the Python launcher, or use setup.ps1 -PythonPath C:\path\python.exe. Supported: 3.10-3.12.'
}
function Backup-Venv([string]$Project) {
    $projectFull=[IO.Path]::GetFullPath($Project).TrimEnd('\')
    $target=[IO.Path]::GetFullPath((Join-Path $Project '.venv'))
    $container=[IO.Path]::GetFullPath((Join-Path $Project 'backups/environments'))
    $destination=Join-Path $container ('venv-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,6))
    if ($target -ine ($projectFull+'\.venv') -or -not $destination.StartsWith($projectFull+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Environment backup failed the project-directory safety check.' }
    $item=Get-Item -LiteralPath $target
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '.venv is a link; preserve it and select an ordinary environment.' }
    New-Item -ItemType Directory -Path $container -Force | Out-Null
    Move-Item -LiteralPath $target -Destination $destination
    Write-Host "Preserved the previous environment at $destination"
}
function Write-EnvironmentMarker([string]$Project,[string]$Python) {
    $info=Get-PythonInfo $Python
    @{project_root=[IO.Path]::GetFullPath($Project);python=$info.version;base_python=$info.base;
      requirements_sha256=(Get-PortableFileHash (Join-Path $Project 'requirements.txt'));
      checked_at_utc=(Get-Date).ToUniversalTime().ToString('o')} |
        ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath (Join-Path $Project '.venv/sherlocked-environment.json')
}


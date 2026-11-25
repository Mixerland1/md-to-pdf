param(
    [Parameter(Mandatory=$true)][string]$InstallDir,
    [Parameter(Mandatory=$true)][string]$Stage,
    [Parameter(Mandatory=$true)][int]$AppPid,
    [switch]$NoRestart
)
$ErrorActionPreference = 'Stop'
$log = Join-Path $Stage 'update.log'
$backup = Join-Path $Stage 'previous'
$new = Join-Path $Stage 'new'
$names = @('MD-to-PDF.exe', '_internal')
$oldMoved = @()
$newMoved = @()
function Log([string]$Message) { Add-Content -LiteralPath $log -Value $Message -Encoding UTF8 }
try {
    if ($AppPid -gt 0) {
        $process = Get-Process -Id $AppPid -ErrorAction SilentlyContinue
        if ($process) { Wait-Process -InputObject $process -Timeout 90 -ErrorAction Stop }
    }
    foreach ($name in $names) {
        if (!(Test-Path -LiteralPath (Join-Path $new $name)) -or !(Test-Path -LiteralPath (Join-Path $InstallDir $name))) { throw "Missing $name" }
    }
    New-Item -ItemType Directory -Path $backup | Out-Null
    foreach ($name in $names) {
        Move-Item -LiteralPath (Join-Path $InstallDir $name) -Destination (Join-Path $backup $name)
        $oldMoved += $name
    }
    foreach ($name in $names) {
        Move-Item -LiteralPath (Join-Path $new $name) -Destination (Join-Path $InstallDir $name)
        $newMoved += $name
    }
    if (!$NoRestart) {
        $process = Start-Process -FilePath (Join-Path $InstallDir 'MD-to-PDF.exe') -WorkingDirectory $InstallDir -PassThru
        Start-Sleep -Seconds 5
        if ($process.HasExited) { throw "New application exited immediately" }
    }
    Log "Update installed. Previous binaries retained at $backup"
} catch {
    Log "Update failed: $_"
    try {
        foreach ($name in $newMoved) {
            Move-Item -LiteralPath (Join-Path $InstallDir $name) -Destination (Join-Path $new $name)
        }
        foreach ($name in $oldMoved) {
            Move-Item -LiteralPath (Join-Path $backup $name) -Destination (Join-Path $InstallDir $name)
        }
        Log 'Previous version restored.'
        if (!$NoRestart -and $oldMoved.Count -gt 0) {
            Start-Process -FilePath (Join-Path $InstallDir 'MD-to-PDF.exe') -WorkingDirectory $InstallDir
        }
    } catch { Log "Rollback failed: $_. Restore from $backup manually." }
    exit 1
}

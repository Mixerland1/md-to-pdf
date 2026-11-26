param(
    [Parameter(Mandatory=$true)][string]$InstallDir,
    [Parameter(Mandatory=$true)][string]$Stage,
    [Parameter(Mandatory=$true)][int]$AppPid,
    [string]$ExpectedVersion = "",
    [switch]$NoRestart
)
$ErrorActionPreference = 'Stop'
$log = Join-Path $Stage 'update.log'
$backup = Join-Path $Stage 'previous'
$new = Join-Path $Stage 'new'
$names = @('MD-to-PDF.exe', '_internal')
$oldMoved = @()
$newMoved = @()
$persistentLog = Join-Path $env:LOCALAPPDATA 'MD-to-PDF\update.log'
function Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
    try {
        New-Item -ItemType Directory -Force -Path (Split-Path $persistentLog) | Out-Null
        Add-Content -LiteralPath $persistentLog -Value $line -Encoding UTF8
    } catch {}
}
function Move-WithRetry([string]$Source,[string]$Destination) {
    for ($i=0; $i -lt 20; $i++) {
        try {
            Move-Item -LiteralPath $Source -Destination $Destination -ErrorAction Stop
            return
        } catch {
            if ($i -eq 19) { throw }
            Start-Sleep -Milliseconds 500
        }
    }
}
function Reset-LauncherEnvironment {
    Get-ChildItem Env: | Where-Object { $_.Name -like '_PYI_*' -or $_.Name -eq '_MEIPASS2' -or $_.Name -eq 'WEASYPRINT_DLL_DIRECTORIES' } | ForEach-Object {
        Remove-Item -LiteralPath ("Env:" + $_.Name) -ErrorAction SilentlyContinue
    }
    $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
}
$launched = $null
try {
    Log "Starting update to $ExpectedVersion in $InstallDir"
    if ($AppPid -gt 0) {
        $process = Get-Process -Id $AppPid -ErrorAction SilentlyContinue
        if ($process) { Wait-Process -InputObject $process -Timeout 90 -ErrorAction Stop }
    }
    foreach ($name in $names) {
        if (!(Test-Path -LiteralPath (Join-Path $new $name)) -or !(Test-Path -LiteralPath (Join-Path $InstallDir $name))) { throw "Missing $name" }
    }
    New-Item -ItemType Directory -Path $backup | Out-Null
    foreach ($name in $names) {
        Move-WithRetry (Join-Path $InstallDir $name) (Join-Path $backup $name)
        $oldMoved += $name
    }
    foreach ($name in $names) {
        Move-WithRetry (Join-Path $new $name) (Join-Path $InstallDir $name)
        $newMoved += $name
    }
    if (!$NoRestart) {
        Reset-LauncherEnvironment
        $ready = Join-Path $Stage 'ready.txt'
        if (!$ExpectedVersion) { throw 'Expected version is required for restart' }
        $arguments = '--update-ready "' + $ready + '"'
        $launched = Start-Process -FilePath (Join-Path $InstallDir 'MD-to-PDF.exe') -ArgumentList $arguments -WorkingDirectory $InstallDir -PassThru
        $deadline = (Get-Date).AddSeconds(90)
        $actual = ""
        while ((Get-Date) -lt $deadline) {
            if ($launched.HasExited) { throw "New application exited: $($launched.ExitCode)" }
            if (Test-Path -LiteralPath $ready) {
                $actual = (Get-Content -LiteralPath $ready -Raw).Trim()
                if ($actual -eq $ExpectedVersion) { break }
                if ($actual) { throw "Expected $ExpectedVersion, launched $actual" }
            }
            Start-Sleep -Milliseconds 250
        }
        if ($actual -ne $ExpectedVersion) { throw 'New application did not confirm startup' }
        Log "Confirmed running version $actual"
    }
    Log "Update installed. Previous binaries retained at $backup"
} catch {
    Log "Update failed: $_"
    try {
        if ($launched -and !$launched.HasExited) {
            Stop-Process -Id $launched.Id -Force
            Wait-Process -Id $launched.Id -ErrorAction SilentlyContinue
        }
        foreach ($name in $newMoved) {
            Move-WithRetry (Join-Path $InstallDir $name) (Join-Path $new $name)
        }
        foreach ($name in $oldMoved) {
            Move-WithRetry (Join-Path $backup $name) (Join-Path $InstallDir $name)
        }
        Log 'Previous version restored.'
        if (!$NoRestart) {
            Reset-LauncherEnvironment
            Start-Process -FilePath (Join-Path $InstallDir 'MD-to-PDF.exe') -WorkingDirectory $InstallDir
        }
    } catch { Log "Rollback failed: $_. Restore from $backup manually." }
    if (!$NoRestart) {
        try {
            Add-Type -AssemblyName System.Windows.Forms
            [void][System.Windows.Forms.MessageBox]::Show(
                "Update failed. See the log: $persistentLog", "MD to PDF")
        } catch {}
    }
    exit 1
}

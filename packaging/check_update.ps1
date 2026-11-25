$ErrorActionPreference = 'Stop'
$root = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
try {
    $install = Join-Path $root 'install'
    $stage = Join-Path $root 'stage'
    New-Item -ItemType Directory -Path "$install/_internal","$stage/new/_internal" -Force | Out-Null
    Set-Content "$install/MD-to-PDF.exe" 'old'
    Set-Content "$install/_internal/test.dll" 'old-lib'
    Set-Content "$install/user.md" 'user-file'
    Set-Content "$stage/new/MD-to-PDF.exe" 'new'
    Set-Content "$stage/new/_internal/test.dll" 'new-lib'
    & "$PSScriptRoot/../src/md_to_pdf/update.ps1" -InstallDir $install -Stage $stage -AppPid 0 -NoRestart
    if ((Get-Content "$install/MD-to-PDF.exe") -ne 'new') { throw 'Update did not replace executable' }
    if ((Get-Content "$install/_internal/test.dll") -ne 'new-lib') { throw 'Update did not replace runtime' }
    if ((Get-Content "$stage/previous/MD-to-PDF.exe") -ne 'old') { throw 'Backup missing' }
    if ((Get-Content "$install/user.md") -ne 'user-file') { throw 'User file changed' }
    Write-Host 'Updater swap smoke test passed'
} finally {
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}

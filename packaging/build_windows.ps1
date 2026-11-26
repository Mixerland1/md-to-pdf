param([Parameter(Mandatory=$true)][string]$MsysPrefix)
$ErrorActionPreference = 'Stop'
$Python = Join-Path $env:pythonLocation 'python.exe'
if (!(Test-Path $Python)) { throw 'CPython from setup-python not found' }
& $Python scripts/fetch_fonts.py
if ($LASTEXITCODE -ne 0) { throw 'Font assets failed verification' }
& $Python -m pip install '.[build,test]'
if ($LASTEXITCODE -ne 0) { throw 'Install failed' }
$env:WEASYPRINT_DLL_DIRECTORIES = Join-Path $MsysPrefix 'bin'
$env:PATH = "$env:WEASYPRINT_DLL_DIRECTORIES;$env:PATH"
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& ./packaging/check_update.ps1
& $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name 'MD-to-PDF' --collect-all md_to_pdf --collect-all pypdfium2 --collect-all pypdfium2_raw --collect-all weasyprint --collect-all tkinterdnd2 --collect-all mistune --collect-all mammoth --collect-all bleach --collect-all openpyxl --collect-all xlrd --add-binary "$env:WEASYPRINT_DLL_DIRECTORIES\*.dll;native" packaging/desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$root = 'dist/MD-to-PDF'
Copy-Item LICENSE,README.md $root
Copy-Item docs "$root/docs" -Recurse
Copy-Item src/md_to_pdf/fonts/*-OFL.txt $root
Copy-Item (Join-Path $MsysPrefix 'share/licenses') "$root/native-licenses" -Recurse
# Record versions and preserve wheel license files for redistribution.
& $Python -m pip freeze | Set-Content "$root/python-dependencies.txt"
Get-ChildItem (& $Python -c "import sysconfig; print(sysconfig.get_path('purelib'))") -Directory -Filter '*.dist-info' | ForEach-Object {
    $d = Join-Path "$root/python-licenses" $_.Name
    New-Item -ItemType Directory -Force $d | Out-Null
    Get-ChildItem $_.FullName -File | Where-Object Name -Match '^(LICENSE|COPYING|NOTICE)' | Copy-Item -Destination $d
    if (Test-Path (Join-Path $_.FullName 'licenses')) { Copy-Item (Join-Path $_.FullName 'licenses') $d -Recurse }
}
# Do not allow the smoke test to silently use the MSYS2 build environment.
Remove-Item Env:WEASYPRINT_DLL_DIRECTORIES
$env:PATH = ($env:PATH.Split(';') | Where-Object { $_ -notlike "$MsysPrefix*" }) -join ';'
$out = Join-Path $PWD 'windows-smoke.pdf'
$p = Start-Process -FilePath "$root/MD-to-PDF.exe" -ArgumentList "--smoke-test `"$PWD/examples/example.md`" `"$out`"" -Wait -PassThru
if ($p.ExitCode -ne 0 -or !(Test-Path $out)) { throw 'Frozen EXE smoke test failed' }
& $Python -c "from pypdf import PdfReader; r=PdfReader('windows-smoke.pdf'); assert 'Руководство' in r.pages[0].extract_text()"
if ($LASTEXITCODE -ne 0) { throw 'Frozen PDF validation failed' }
$brand = Join-Path $PWD 'windows-brand.pdf'
$p = Start-Process -FilePath "$root/MD-to-PDF.exe" -ArgumentList "--brand-smoke-test `"$PWD/examples/granulex-style-check.md`" `"$brand`"" -Wait -PassThru
if ($p.ExitCode -ne 0 -or !(Test-Path $brand)) { throw 'Frozen brand smoke test failed' }
& $Python packaging/check_smoke.py $out $brand
if ($LASTEXITCODE -ne 0) { throw 'Frozen brand PDF validation failed' }
$expectedVersion = (& $Python -c "from md_to_pdf import __version__; print(__version__)").Trim()
$versionFile = Join-Path $PWD 'windows-version.txt'
$p = Start-Process -FilePath "$root/MD-to-PDF.exe" -ArgumentList ('--version-file "' + $versionFile + '"') -Wait -PassThru
if ($p.ExitCode -ne 0 -or !(Test-Path $versionFile) -or (Get-Content $versionFile -Raw).Trim() -ne $expectedVersion) { throw 'Frozen version mismatch' }
Compress-Archive -Path $root -DestinationPath 'MD-to-PDF-Windows-x64.zip' -Force

# Build the installer and check install/uninstall on the disposable runner.
$ISCC = Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Inno Setup 6\ISCC.exe'
if (!(Test-Path $ISCC)) {
    choco install innosetup --yes --no-progress
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup installation failed' }
}
if (!(Test-Path $ISCC)) { throw 'Inno Setup compiler not found' }
$version = (& $Python -c "from md_to_pdf import __version__; print(__version__)").Trim()
& $ISCC "/DAppVersion=$version" packaging/setup.iss
if ($LASTEXITCODE -ne 0 -or !(Test-Path 'MD-to-PDF-Windows-Setup.exe')) { throw 'Installer build failed' }
$installed = Join-Path $env:RUNNER_TEMP 'md-to-pdf-install-smoke'
$args = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="" /DIR="' + $installed + '"'
$setup = Start-Process -FilePath (Join-Path $PWD 'MD-to-PDF-Windows-Setup.exe') -ArgumentList $args -Wait -PassThru
if ($setup.ExitCode -ne 0 -or !(Test-Path "$installed/MD-to-PDF.exe") -or !(Test-Path "$installed/unins000.exe")) { throw 'Installer smoke failed' }
try {
    $installedPdf = Join-Path $env:RUNNER_TEMP 'md-to-pdf-installed-smoke.pdf'
    $args = '--smoke-test "' + (Join-Path $PWD 'examples/example.md') + '" "' + $installedPdf + '"'
    $p = Start-Process -FilePath "$installed/MD-to-PDF.exe" -ArgumentList $args -Wait -PassThru
    if ($p.ExitCode -ne 0 -or !(Test-Path $installedPdf)) { throw 'Installed EXE smoke failed' }
} finally {
    $u = Start-Process -FilePath "$installed/unins000.exe" -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait -PassThru
    if ($u.ExitCode -ne 0) { throw 'Uninstall smoke failed' }
}

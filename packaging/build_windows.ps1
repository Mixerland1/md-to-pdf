param([Parameter(Mandatory=$true)][string]$MsysPrefix)
$ErrorActionPreference = 'Stop'
$Python = Join-Path $env:pythonLocation 'python.exe'
if (!(Test-Path $Python)) { throw 'CPython from setup-python not found' }
& $Python -m pip install '.[build,test]'
if ($LASTEXITCODE -ne 0) { throw 'Install failed' }
$env:WEASYPRINT_DLL_DIRECTORIES = Join-Path $MsysPrefix 'bin'
$env:PATH = "$env:WEASYPRINT_DLL_DIRECTORIES;$env:PATH"
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name 'MD-to-PDF' --collect-all md_to_pdf --collect-all weasyprint --collect-all tkinterdnd2 --collect-all mistune --add-binary "$env:WEASYPRINT_DLL_DIRECTORIES\*.dll;native" packaging/desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$root = 'dist/MD-to-PDF'
Copy-Item LICENSE,README.md $root
Copy-Item (Join-Path $MsysPrefix 'share/licenses') "$root/native-licenses" -Recurse
# Record versions and preserve wheel license files for redistribution.
python -m pip freeze | Set-Content "$root/python-dependencies.txt"
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
Compress-Archive -Path $root -DestinationPath 'MD-to-PDF-Windows-x64.zip' -Force

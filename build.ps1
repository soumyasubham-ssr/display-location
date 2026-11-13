# Build dist\DisplayLocation.exe (TASK-010, ARCHITECTURE §15, D-007, D-008).
# Run from the activated venv:  .\build.ps1

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

# PyInstaller logs to stderr. In Windows PowerShell 5.1 that becomes an error
# record, which 'Stop' would turn fatal, so native calls run with 'Continue'
# and are judged by their exit code.
function Invoke-Native([scriptblock]$cmd) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $cmd } finally { $ErrorActionPreference = $prev }
}

# --- checks ------------------------------------------------------------------
if (-not $env:VIRTUAL_ENV) {
    Write-Error "No virtual environment is active. Run:  & `"`$env:LOCALAPPDATA\venvs\display-location\Scripts\Activate.ps1`"  then  .\build.ps1"
    exit 1
}
$python = Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'
Invoke-Native { & $python -m PyInstaller --version *> $null }
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller is not installed in $env:VIRTUAL_ENV. Run:  pip install -r requirements-dev.txt"
    exit 1
}

# --- version info (from src\display_location\__init__.py) --------------------
$init = Get-Content (Join-Path $root 'src\display_location\__init__.py') -Raw
if ($init -notmatch '__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"') {
    Write-Error "Could not read __version__ from src\display_location\__init__.py"
    exit 1
}
$ver = "$($Matches[1]).$($Matches[2]).$($Matches[3])"
$tuple = "$($Matches[1]), $($Matches[2]), $($Matches[3]), 0"

# Work folders outside OneDrive (D-008).
$tmp = Join-Path $env:LOCALAPPDATA 'DisplayLocation\build-tmp'
New-Item -ItemType Directory -Force $tmp | Out-Null
$versionFile = Join-Path $tmp 'version_info.txt'
$versionText = @"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($tuple), prodvers=($tuple), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Display Location'),
      StringStruct('FileDescription', 'Display Location'),
      StringStruct('FileVersion', '$ver'),
      StringStruct('InternalName', 'DisplayLocation'),
      StringStruct('OriginalFilename', 'DisplayLocation.exe'),
      StringStruct('ProductName', 'Display Location'),
      StringStruct('ProductVersion', '$ver'),
      StringStruct('LegalCopyright', 'MIT License')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@
# UTF-8 without BOM: PowerShell 5.1's Out-File -Encoding utf8 adds one, which PyInstaller can't parse.
[System.IO.File]::WriteAllText($versionFile, $versionText, (New-Object System.Text.UTF8Encoding $false))

# --- build -------------------------------------------------------------------
Write-Host "Building Display Location $ver ..."
Invoke-Native { & $python -m PyInstaller --noconfirm --clean --onefile --windowed --name DisplayLocation `
    --icon "$root\assets\icon.ico" `
    --add-data "$root\assets\icon.ico;assets" `
    --version-file $versionFile `
    --distpath "$root\dist" `
    --workpath $tmp `
    --specpath $tmp `
    --paths "$root\src" `
    "$root\src\display_location\__main__.py" 2>&1 | ForEach-Object { "$_" } }
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

$exe = Get-Item "$root\dist\DisplayLocation.exe"
$mb = [math]::Round($exe.Length / 1MB, 1)
Write-Host ""
Write-Host "Built $($exe.FullName)  ($mb MB, version $ver)"

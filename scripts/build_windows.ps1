[CmdletBinding()]
param(
    [string]$Version = "1.0.0",
    [string]$Python = "",
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ExpectedVersion = (& {
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"
    if ($Python) {
        & $Python -c "import cleandrop; print(cleandrop.__version__)"
    }
    elseif (Test-Path -LiteralPath (Join-Path $ProjectRoot "tools\python312\python.exe")) {
        & (Join-Path $ProjectRoot "tools\python312\python.exe") -c "import cleandrop; print(cleandrop.__version__)"
    }
    else {
        & py -3.12 -c "import cleandrop; print(cleandrop.__version__)"
    }
})
if ($ExpectedVersion -ne $Version) {
    throw "Requested version $Version does not match package version $ExpectedVersion"
}

if (-not $Python) {
    $ProjectPython = Join-Path $ProjectRoot "tools\python312\python.exe"
    if (Test-Path -LiteralPath $ProjectPython) {
        $Python = $ProjectPython
    }
    else {
        $Python = (& py -3.12 -c "import sys; print(sys.executable)")
    }
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python 3.12 executable was not found"
}
$PythonVersion = (& $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ($PythonVersion -ne "3.12") {
    throw "Release builds require Python 3.12; found $PythonVersion"
}

$BuildVenv = Join-Path $ProjectRoot ".build-venv"
if (-not (Test-Path -LiteralPath (Join-Path $BuildVenv "Scripts\python.exe"))) {
    & $Python -m venv $BuildVenv
}
$BuildPython = Join-Path $BuildVenv "Scripts\python.exe"
& $BuildPython -m pip install --upgrade pip
& $BuildPython -m pip install -e "$ProjectRoot[dev]"

if (
    -not (Test-Path -LiteralPath (Join-Path $ProjectRoot "vendor\tesseract\tesseract.exe")) -or
    -not (Test-Path -LiteralPath (Join-Path $ProjectRoot "vendor\exiftool\exiftool.exe"))
) {
    & (Join-Path $ProjectRoot "scripts\provision_windows_tools.ps1")
}

if (-not $SkipTests) {
    Push-Location $ProjectRoot
    try {
        & $BuildPython -m pytest -q --cov=cleandrop --cov-branch --cov-fail-under=85
        & $BuildPython -m ruff check .
        & $BuildPython -m ruff format --check .
        & $BuildPython -m mypy src\cleandrop
    }
    finally {
        Pop-Location
    }
}

$BuildDirectory = Join-Path $ProjectRoot "build"
$DistDirectory = Join-Path $ProjectRoot "dist"
foreach ($Target in @($BuildDirectory, $DistDirectory)) {
    $ResolvedParent = (Resolve-Path (Split-Path $Target -Parent)).Path
    if ($ResolvedParent -ne $ProjectRoot) {
        throw "Refusing to clear a build path outside the project root: $Target"
    }
    if (Test-Path -LiteralPath $Target) {
        Remove-Item -LiteralPath $Target -Recurse -Force
    }
}

Push-Location $ProjectRoot
try {
    & $BuildPython -m PyInstaller --clean --noconfirm .\packaging\cleandrop.spec
}
finally {
    Pop-Location
}

$PortableDirectory = Join-Path $DistDirectory "CleanDrop"
$Cli = Join-Path $PortableDirectory "cleandrop-cli.exe"
$Gui = Join-Path $PortableDirectory "CleanDrop.exe"
if (-not (Test-Path -LiteralPath $Cli) -or -not (Test-Path -LiteralPath $Gui)) {
    throw "PyInstaller did not create both Windows executables"
}

$Doctor = (& $Cli doctor | ConvertFrom-Json)
foreach ($Capability in @("Tesseract", "fas.traineddata", "eng.traineddata", "osd.traineddata", "ExifTool")) {
    if (-not $Doctor.$Capability.available) {
        throw "Portable doctor check failed for $Capability"
    }
}

$PortableZip = Join-Path $DistDirectory "CleanDrop-$Version-win-x64.zip"
if (Test-Path -LiteralPath $PortableZip) {
    Remove-Item -LiteralPath $PortableZip -Force
}
Compress-Archive -LiteralPath $PortableDirectory -DestinationPath $PortableZip -CompressionLevel Optimal

if (-not $SkipInstaller) {
    $CompilerCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
        (Join-Path $ProjectRoot "tools\inno\ISCC.exe")
    )
    $Compiler = $CompilerCandidates |
        Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
        Select-Object -First 1
    if (-not $Compiler) {
        throw "Inno Setup compiler was not found. Use -SkipInstaller only for a portable-only build."
    }
    & $Compiler "/DMyAppVersion=$Version" (Join-Path $ProjectRoot "packaging\cleandrop.iss")
}

$ReleaseFiles = @($PortableZip)
$Installer = Join-Path $DistDirectory "installer\CleanDrop-Setup-$Version.exe"
if (Test-Path -LiteralPath $Installer) {
    $ReleaseFiles += $Installer
}
$ChecksumPath = Join-Path $DistDirectory "SHA256SUMS.txt"
$ChecksumLines = foreach ($File in $ReleaseFiles) {
    $Hash = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant()
    "$Hash  $([IO.Path]::GetFileName($File))"
}
$ChecksumLines | Set-Content -LiteralPath $ChecksumPath -Encoding ASCII
Write-Output "Built CleanDrop $Version"
Get-Item -LiteralPath ($ReleaseFiles + $ChecksumPath) | Select-Object FullName, Length

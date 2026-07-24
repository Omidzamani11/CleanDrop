[CmdletBinding()]
param(
    [string]$TesseractSource = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Downloads = Join-Path $ProjectRoot "downloads"
$Vendor = Join-Path $ProjectRoot "vendor"
$TesseractTarget = Join-Path $Vendor "tesseract"
$ExifToolTarget = Join-Path $Vendor "exiftool"
New-Item -ItemType Directory -Path $Downloads, $TesseractTarget, $ExifToolTarget -Force | Out-Null

function Get-RemoteFile {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Destination,
        [string]$Sha256 = ""
    )
    if ((Test-Path -LiteralPath $Destination) -and -not $Force) {
        if (-not $Sha256) {
            return
        }
        $CachedHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($CachedHash -eq $Sha256) {
            return
        }
        throw "Checksum mismatch for cached download $Destination"
    }
    Invoke-WebRequest -Uri $Uri -OutFile $Destination -UseBasicParsing
    if ($Sha256) {
        $DownloadedHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($DownloadedHash -ne $Sha256) {
            throw "Checksum mismatch for downloaded file $Destination"
        }
    }
}

if (-not $TesseractSource) {
    $Candidates = @(
        (Join-Path $env:ProgramFiles "Tesseract-OCR"),
        (Join-Path ${env:ProgramFiles(x86)} "Tesseract-OCR"),
        (Join-Path $ProjectRoot "tools\Tesseract-OCR")
    )
    $TesseractSource = $Candidates |
        Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $_ "tesseract.exe")) } |
        Select-Object -First 1
}

if (-not $TesseractSource) {
    $Installer = Join-Path $Downloads "tesseract-ocr-w64-setup-5.5.0.20241111.exe"
    Get-RemoteFile `
        -Uri "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe" `
        -Destination $Installer `
        -Sha256 "F3FC4236425B690C8BE756F35793F77394EE004BE0A6460A440C754D892F68BC"
    $TesseractSource = Join-Path $ProjectRoot "tools\Tesseract-OCR"
    New-Item -ItemType Directory -Path $TesseractSource -Force | Out-Null
    $Process = Start-Process `
        -FilePath $Installer `
        -ArgumentList @("/S", "/D=$TesseractSource") `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    if ($Process.ExitCode -ne 0) {
        throw "Tesseract installer failed with exit code $($Process.ExitCode)"
    }
}

$TesseractExecutable = Join-Path $TesseractSource "tesseract.exe"
if (-not (Test-Path -LiteralPath $TesseractExecutable)) {
    throw "Tesseract runtime was not found at $TesseractSource"
}

Get-ChildItem -LiteralPath $TesseractSource -File |
    Where-Object { $_.Extension -eq ".dll" -or $_.Name -eq "tesseract.exe" } |
    Copy-Item -Destination $TesseractTarget -Force

$TessdataTarget = Join-Path $TesseractTarget "tessdata"
New-Item -ItemType Directory -Path $TessdataTarget -Force | Out-Null
foreach ($Folder in @("configs", "tessconfigs")) {
    $SourceFolder = Join-Path (Join-Path $TesseractSource "tessdata") $Folder
    if (Test-Path -LiteralPath $SourceFolder) {
        Copy-Item -LiteralPath $SourceFolder -Destination $TessdataTarget -Recurse -Force
    }
}

$TessdataBase = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main"
foreach ($Language in @("fas", "eng", "osd")) {
    Get-RemoteFile `
        -Uri "$TessdataBase/$Language.traineddata" `
        -Destination (Join-Path $TessdataTarget "$Language.traineddata")
}

$ExifToolZip = Join-Path $Downloads "exiftool-13.59_64.zip"
Get-RemoteFile `
    -Uri "https://sourceforge.net/projects/exiftool/files/exiftool-13.59_64.zip/download" `
    -Destination $ExifToolZip
$ExtractRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("cleandrop-exiftool-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $ExtractRoot | Out-Null
try {
    Expand-Archive -LiteralPath $ExifToolZip -DestinationPath $ExtractRoot
    $ExifExecutable = Get-ChildItem -LiteralPath $ExtractRoot -Recurse -File |
        Where-Object { $_.Name -like "exiftool*.exe" } |
        Select-Object -First 1
    $ExifFiles = Get-ChildItem -LiteralPath $ExtractRoot -Recurse -Directory |
        Where-Object { $_.Name -eq "exiftool_files" } |
        Select-Object -First 1
    if (-not $ExifExecutable -or -not $ExifFiles) {
        throw "The ExifTool archive did not contain the expected portable runtime"
    }
    Copy-Item -LiteralPath $ExifExecutable.FullName -Destination (Join-Path $ExifToolTarget "exiftool.exe") -Force
    Copy-Item -LiteralPath $ExifFiles.FullName -Destination $ExifToolTarget -Recurse -Force
}
finally {
    if (Test-Path -LiteralPath $ExtractRoot) {
        Remove-Item -LiteralPath $ExtractRoot -Recurse -Force
    }
}

$TesseractVersion = (& (Join-Path $TesseractTarget "tesseract.exe") --version 2>&1 | Select-Object -First 1)
$ExifToolVersion = (& (Join-Path $ExifToolTarget "exiftool.exe") -ver)
$Languages = (& (Join-Path $TesseractTarget "tesseract.exe") --tessdata-dir $TessdataTarget --list-langs 2>&1) -join "`n"
foreach ($RequiredLanguage in @("fas", "eng", "osd")) {
    if ($Languages -notmatch "(?m)^$RequiredLanguage$") {
        throw "Tesseract language $RequiredLanguage is unavailable"
    }
}

$Manifest = [ordered]@{
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    tesseract = [ordered]@{
        version = [string]$TesseractVersion
        languages = @("fas", "eng", "osd")
        executable_sha256 = (Get-FileHash -LiteralPath (Join-Path $TesseractTarget "tesseract.exe") -Algorithm SHA256).Hash
    }
    exiftool = [ordered]@{
        version = [string]$ExifToolVersion
        executable_sha256 = (Get-FileHash -LiteralPath (Join-Path $ExifToolTarget "exiftool.exe") -Algorithm SHA256).Hash
    }
}
$Manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $Vendor "manifest.json") -Encoding UTF8
Write-Output "Provisioned Tesseract $TesseractVersion with fas+eng+osd and ExifTool $ExifToolVersion"

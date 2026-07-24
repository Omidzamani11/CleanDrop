# Development

## Toolchain

- Python 3.12 x64
- PySide6 / Qt Widgets
- Pillow
- PyMuPDF and pikepdf
- Tesseract CLI
- ExifTool CLI
- pytest, pytest-cov, Ruff, mypy
- PyInstaller
- Inno Setup for the Windows installer

No database or web server is used.

## Environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run:

```powershell
.\.venv\Scripts\python.exe -m cleandrop
.\.venv\Scripts\cleandrop.exe doctor
```

## Quality gates

All four commands must pass:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy src\cleandrop
```

Coverage:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=cleandrop --cov-branch --cov-fail-under=85
```

Tests use generated synthetic data and do not access the internet. Windows E2E
tests exercise the actual Qt window, worker process, OCR runtime, output, and report.

## External tools

For release builds, provision the pinned local runtime:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\provision_windows_tools.ps1
```

The script copies a Tesseract runtime, downloads `fas`, `eng`, and `osd`
`tessdata_fast` files, and extracts ExifTool into ignored `vendor/` directories.
It is a build-time network operation; the application never runs it.

## Windows build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Outputs:

- `dist/CleanDrop/` — one-directory portable application;
- `dist/CleanDrop-1.0.0-win-x64.zip` — portable archive;
- `dist/installer/CleanDrop-Setup-1.0.0.exe` — per-user installer if Inno Setup is available;
- `dist/SHA256SUMS.txt` — digests.

The GUI executable is windowed. `cleandrop-cli.exe` is a console executable and
contains the same processing code. The GUI starts itself with `--worker` for local
file processing.

## Release process

1. Update the version and changelog.
2. Run all quality gates on Python 3.12.
3. Build and test the portable directory.
4. Install into a clean user profile and run the desktop E2E smoke flow.
5. Tag `vX.Y.Z`.
6. The release workflow rebuilds on Windows, creates checksums, and attaches the
   installer and portable ZIP.

Never commit the ignored `vendor/`, `downloads/`, `tools/`, `build/`, or `dist/`
directories.

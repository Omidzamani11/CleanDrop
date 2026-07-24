# Contributing to CleanDrop

Thank you for helping improve a privacy tool. Contributions must preserve the
local-only security boundary and the mandatory pipeline:

`Inspect → Detect → Review → Plan → Sanitize → Verify → Report`

## Before opening a change

1. Use a synthetic fixture; never commit real personal documents.
2. Keep excluded features out of scope: no cloud, login, account, LLM, AI API,
   malware scanner, browser extension, face detection, or mobile application.
3. Discuss changes that alter the threat model, report schema, or verification
   policy in an issue before implementation.
4. Add a regression test before or with every security fix.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Required checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=cleandrop --cov-branch --cov-fail-under=85
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy src\cleandrop
```

## Design rules

- Domain code must not import PySide6, Pillow, PyMuPDF, pikepdf, or external tools.
- UI code must send work to the isolated worker rather than process files directly.
- Use `pathlib`, typed dataclasses/enums, and protocols at layer boundaries.
- Never use `shell=True`, log raw OCR/PII, trust an extension, copy source PDF
  objects into a flattened PDF, or overwrite an original.
- Every successful job must enter `VERIFYING` before completion.
- Atomic output and cancellation behavior require tests.
- User-facing English and Persian strings belong in the translation catalog.

## Pull requests

Keep a pull request focused, explain its security impact, list the commands run,
and include before/after screenshots for visible UI changes. By contributing,
you agree that your contribution is licensed under `AGPL-3.0-or-later`.

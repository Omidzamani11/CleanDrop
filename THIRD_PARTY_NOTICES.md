# Third-party notices

CleanDrop 1.0.0 is distributed under `AGPL-3.0-or-later`. Its Windows bundle
also includes or depends on the projects below. Their licenses remain in force;
this notice is not a substitute for their license texts.

| Component | Purpose | License |
|---|---|---|
| Python | Runtime | Python Software Foundation License |
| PySide6 / Qt | Desktop UI | LGPL-3.0-only / GPL / commercial options as published by Qt |
| Pillow | Image decoding and encoding | HPND |
| PyMuPDF | PDF rendering and text inspection | AGPL-3.0-or-later |
| MuPDF | PDF engine used by PyMuPDF | AGPL-3.0-or-later |
| pikepdf / qpdf | PDF structure inspection | MPL-2.0 / Apache-2.0 |
| Tesseract OCR | Local OCR | Apache-2.0 |
| Leptonica | Imaging used by Tesseract | BSD-2-Clause |
| tessdata_fast `fas`, `eng`, `osd` | OCR language data | Apache-2.0 |
| ExifTool | Metadata inspection | Artistic License 1.0 or GPL-1.0-or-later |
| PyInstaller | Windows freezing tool | GPL-2.0-or-later with bootloader exception |
| Inno Setup | Windows installer builder | Inno Setup License |

Authoritative project/license pages:

- Python: <https://docs.python.org/3/license.html>
- Qt for Python: <https://doc.qt.io/qtforpython-6/licenses.html>
- Pillow: <https://github.com/python-pillow/Pillow/blob/main/LICENSE>
- PyMuPDF: <https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright>
- pikepdf: <https://github.com/pikepdf/pikepdf/blob/main/LICENSE.txt>
- qpdf: <https://github.com/qpdf/qpdf/blob/main/NOTICE.md>
- Tesseract: <https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE>
- tessdata_fast: <https://github.com/tesseract-ocr/tessdata_fast/blob/main/LICENSE>
- ExifTool: <https://exiftool.org/index.html>
- PyInstaller: <https://pyinstaller.org/en/stable/license.html>
- Inno Setup: <https://jrsoftware.org/files/is/license.txt>

The source repository does not commit downloaded Windows tool binaries.
Release automation provisions pinned tool versions and bundles them into the
Windows artifact. See `scripts/provision_windows_tools.ps1`.

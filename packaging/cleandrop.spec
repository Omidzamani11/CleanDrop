# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"

datas = [
    (str(SRC / "cleandrop" / "resources"), "src/cleandrop/resources"),
    (str(ROOT / "vendor" / "tesseract"), "vendor/tesseract"),
    (str(ROOT / "vendor" / "exiftool"), "vendor/exiftool"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
]

hiddenimports = (
    collect_submodules("PIL")
    + collect_submodules("pikepdf")
    + collect_submodules("fitz")
)

analysis = Analysis(
    [str(SRC / "cleandrop" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

gui = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="CleanDrop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SRC / "cleandrop" / "resources" / "cleandrop-icon.ico"),
    version=str(ROOT / "packaging" / "version_info.txt"),
)

cli = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="cleandrop-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SRC / "cleandrop" / "resources" / "cleandrop-icon.ico"),
    version=str(ROOT / "packaging" / "version_info.txt"),
)

bundle = COLLECT(
    gui,
    cli,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CleanDrop",
)

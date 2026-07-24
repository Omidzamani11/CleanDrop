from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from PIL import Image, PngImagePlugin, TiffImagePlugin


@pytest.fixture
def jpg_with_metadata(tmp_path: Path) -> Path:
    path = tmp_path / "عکس دارای فاصله.jpg"
    image = Image.new("RGB", (320, 200), "white")
    exif = Image.Exif()
    exif[271] = "Secret Camera Corp"
    exif[272] = "Tracking Model 42"
    exif[305] = "Private Editor"
    image.save(path, exif=exif)
    return path


@pytest.fixture
def png_with_text(tmp_path: Path) -> Path:
    path = tmp_path / "metadata.png"
    image = Image.new("RGB", (200, 100), "white")
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Description", "owner@example.com")
    image.save(path, pnginfo=metadata)
    return path


@pytest.fixture
def jpg_with_orientation(tmp_path: Path) -> Path:
    path = tmp_path / "rotated-camera.jpg"
    image = Image.new("RGB", (80, 40), "white")
    exif = Image.Exif()
    exif[274] = 6
    image.save(path, exif=exif)
    return path


@pytest.fixture
def jpg_with_gps(tmp_path: Path) -> Path:
    path = tmp_path / "location.jpg"
    rational = TiffImagePlugin.IFDRational
    exif = Image.Exif()
    exif[34853] = {
        1: "N",
        2: (rational(35), rational(41), rational(0)),
        3: "E",
        4: (rational(51), rational(25), rational(0)),
    }
    Image.new("RGB", (100, 60), "white").save(path, exif=exif)
    return path


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "private document.pdf"
    document = fitz.open()
    page = document.new_page(width=400, height=300)
    page.insert_text((40, 80), "Contact owner@example.com or 09123456789")
    page.add_text_annot((40, 120), "private note")
    document.set_metadata(
        {
            "author": "Private Person",
            "title": "Sensitive title",
            "subject": "Not for sharing",
        }
    )
    document.save(path)
    document.close()
    return path


@pytest.fixture
def scanned_pdf(tmp_path: Path) -> Path:
    image_path = tmp_path / "scan.png"
    Image.new("RGB", (400, 300), "white").save(image_path)
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page(width=400, height=300)
    page.insert_image(page.rect, filename=image_path)
    document.save(path)
    document.close()
    return path

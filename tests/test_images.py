import io

from PIL import Image

from pdfflatten import render
from pdfflatten.images import pdf_to_jpegs


def test_one_jpeg_per_page(base_pdf):
    jpgs = pdf_to_jpegs(base_pdf.read_bytes())
    assert len(jpgs) == 1


def test_outputs_are_jpeg(base_pdf):
    jpgs = pdf_to_jpegs(base_pdf.read_bytes())
    for data in jpgs:
        assert data[:2] == b"\xff\xd8"  # JPEG SOI marker
        assert data[-2:] == b"\xff\xd9"  # JPEG EOI marker


def test_respects_max_bytes(base_pdf):
    # A tiny cap forces the quality/DPI ladder all the way down; still a JPEG.
    jpgs = pdf_to_jpegs(base_pdf.read_bytes(), max_bytes=1)
    assert jpgs and jpgs[0][:2] == b"\xff\xd8"


def test_each_image_under_default_limit(base_pdf):
    jpgs = pdf_to_jpegs(base_pdf.read_bytes())
    assert all(len(d) < 25 * 1024 * 1024 for d in jpgs)


def test_render_pixels_are_capped(base_pdf, monkeypatch):
    # Same guard as the flattener: a hostile page size must not force a
    # gigantic render allocation.
    monkeypatch.setattr(render, "MAX_RENDER_PIXELS", 100_000)
    jpgs = pdf_to_jpegs(base_pdf.read_bytes())
    image = Image.open(io.BytesIO(jpgs[0]))
    # Small slack for pdfium rounding partial pixels up at the edges.
    assert image.width * image.height <= 105_000

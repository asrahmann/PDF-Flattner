import io
import threading

import pikepdf
import pypdfium2 as pdfium
import pytest

from pdfflatten import render
from pdfflatten.decrypt import decrypt_to_bytes
from pdfflatten.flatten import flatten_pdf_bytes
from pdfflatten.render import Cancelled


def _page_count(data):
    doc = pdfium.PdfDocument(data)
    n = len(doc)
    doc.close()
    return n


def test_output_is_valid_pdf(base_pdf):
    out = flatten_pdf_bytes(base_pdf.read_bytes())
    assert out[:5] == b"%PDF-"


def test_page_count_preserved(base_pdf):
    src_n = _page_count(base_pdf.read_bytes())
    out_n = _page_count(flatten_pdf_bytes(base_pdf.read_bytes()))
    assert out_n == src_n == 1


def test_form_fields_removed(form_pdf):
    out = flatten_pdf_bytes(form_pdf.read_bytes())
    pdf = pikepdf.open(io.BytesIO(out))
    # A flattened/rasterized PDF must not carry an interactive AcroForm.
    assert "/AcroForm" not in pdf.Root


def test_output_not_encrypted(owner_encrypted_pdf):
    decrypted = decrypt_to_bytes(owner_encrypted_pdf)
    out = flatten_pdf_bytes(decrypted)
    pdf = pikepdf.open(io.BytesIO(out))
    assert not pdf.is_encrypted


def test_output_is_compact(base_pdf):
    # A bitonal/CCITT-G4 text page must be small (was multi-hundred-KB as JPEG).
    out = flatten_pdf_bytes(base_pdf.read_bytes())
    assert len(out) < 200_000


def test_max_bytes_triggers_downscale(base_pdf):
    # An impossibly small cap forces the DPI ladder to the bottom; still valid PDF.
    out = flatten_pdf_bytes(base_pdf.read_bytes(), max_bytes=1)
    assert out[:5] == b"%PDF-"
    assert _page_count(out) == 1


def _embedded_image_pixels(pdf_bytes):
    """Width * height of the (single) raster image on page 1."""
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    image = next(iter(pdf.pages[0].images.values()))
    return int(image.Width) * int(image.Height)


def test_render_pixels_are_capped(base_pdf, monkeypatch):
    # A hostile PDF can declare an enormous page; the renderer must never
    # allocate more than the pixel budget no matter what the page claims.
    monkeypatch.setattr(render, "MAX_RENDER_PIXELS", 100_000)
    out = flatten_pdf_bytes(base_pdf.read_bytes())
    # Small slack for pdfium rounding partial pixels up at the edges.
    assert _embedded_image_pixels(out) <= 105_000


def test_clamped_page_keeps_physical_size(base_pdf, monkeypatch):
    # Clamping lowers the effective DPI; the page must still print letter-size.
    monkeypatch.setattr(render, "MAX_RENDER_PIXELS", 100_000)
    out = flatten_pdf_bytes(base_pdf.read_bytes())
    pdf = pikepdf.open(io.BytesIO(out))
    box = pdf.pages[0].mediabox
    width = float(box[2]) - float(box[0])
    height = float(box[3]) - float(box[1])
    assert width == pytest.approx(612, rel=0.03)
    assert height == pytest.approx(792, rel=0.03)


def test_progress_called_once_per_page(multi_page_pdf):
    calls = []
    flatten_pdf_bytes(
        multi_page_pdf.read_bytes(),
        progress=lambda cur, total, phase: calls.append((cur, total, phase)),
    )
    # Default cap is generous: a single pass over 3 pages.
    assert calls == [(1, 3, "Flattening"), (2, 3, "Flattening"), (3, 3, "Flattening")]


def test_progress_reports_reducing_size_pass(multi_page_pdf):
    phases = set()
    flatten_pdf_bytes(
        multi_page_pdf.read_bytes(),
        max_bytes=1,  # impossibly small: forces the DPI ladder to re-render
        progress=lambda cur, total, phase: phases.add(phase),
    )
    assert "Flattening" in phases
    assert "Reducing size" in phases


def test_cancel_raises_before_finishing(multi_page_pdf):
    cancel = threading.Event()
    cancel.set()  # already cancelled: must stop at the first page
    with pytest.raises(Cancelled):
        flatten_pdf_bytes(multi_page_pdf.read_bytes(), cancel=cancel)

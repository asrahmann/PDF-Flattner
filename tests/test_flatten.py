import io

import pikepdf
import pypdfium2 as pdfium

from pdfflatten.decrypt import decrypt_to_bytes
from pdfflatten.flatten import flatten_pdf_bytes


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

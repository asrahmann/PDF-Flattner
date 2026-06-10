"""Flatten a PDF by rasterizing each page to a fax-native bitonal image.

Pages are rendered to 1-bit black-and-white and embedded with CCITT Group 4
compression — the same format fax machines use. This produces tiny files (a
text page is typically tens of KB) with no loss of fax quality, since a fax is
black-and-white at ~200 dpi anyway. If the result still exceeds a size limit,
the resolution is stepped down automatically until it fits.
"""

import io

import img2pdf
import pikepdf
import pypdfium2 as pdfium
from PIL import Image

FAX_DPI = 200
# Common fax APIs cap uploads around 30 MB; stay comfortably under that.
DEFAULT_MAX_BYTES = 25 * 1024 * 1024
# Resolutions to fall back to (descending) if the file is still too large.
_DPI_LADDER = (200, 150, 120, 100)


def _render_pages(pdf_bytes: bytes, dpi: int) -> list[bytes]:
    """Render every page to a 1-bit PNG at ``dpi``, returning the PNG bytes."""
    doc = pdfium.PdfDocument(pdf_bytes)
    scale = dpi / 72.0
    images: list[bytes] = []
    try:
        for page in doc:
            bitmap = page.render(scale=scale, grayscale=True)
            gray = bitmap.to_pil().convert("L")
            # Threshold to bilevel (no dithering) — crisp text and best G4 compression.
            bw = gray.convert("1", dither=Image.NONE)
            buf = io.BytesIO()
            # Embed the DPI so img2pdf sizes each page to its true physical size.
            bw.save(buf, format="PNG", dpi=(dpi, dpi))
            images.append(buf.getvalue())
            page.close()
    finally:
        doc.close()
    return images


def _assemble(images: list[bytes]) -> bytes:
    """Build a linearized PDF from 1-bit page images (img2pdf uses CCITT G4)."""
    assembled = img2pdf.convert(images)
    pdf = pikepdf.open(io.BytesIO(assembled))
    out = io.BytesIO()
    with pdf:
        pdf.save(out, linearize=True)
    return out.getvalue()


def flatten_pdf_bytes(
    pdf_bytes: bytes, dpi: int = FAX_DPI, max_bytes: int | None = DEFAULT_MAX_BYTES
) -> bytes:
    """Rasterize ``pdf_bytes`` to a flat, fax-ready, bitonal PDF.

    The result has no forms, annotations, transparency, or interactivity. Output
    is rendered at ``dpi``; if ``max_bytes`` is set and the file exceeds it, the
    resolution is reduced step by step until it fits (or the lowest is reached).
    """
    candidate_dpis = (dpi, *(d for d in _DPI_LADDER if d < dpi))
    result = b""
    for candidate_dpi in candidate_dpis:
        result = _assemble(_render_pages(pdf_bytes, candidate_dpi))
        if max_bytes is None or len(result) <= max_bytes:
            return result
    return result  # smallest we could produce, even if still over the limit

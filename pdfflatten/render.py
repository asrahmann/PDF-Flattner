"""Guard rails and pre-render inspection for untrusted PDFs.

A hostile PDF can declare pages up to the spec maximum of 200x200 inches
(14400x14400 pt). Rendered at fax DPI that would be a multi-gigabyte
allocation per page — an easy way to freeze or crash the machine. Instead of
trusting the page size, every render goes through a fixed pixel budget: pages
that would exceed it are rendered at a proportionally lower scale (the page
keeps its physical print size; only the effective DPI drops).

This module also exposes ``page_count`` (a cheap pre-render check used to warn
about long documents) and the ``Cancelled`` exception raised when a render is
cancelled mid-flight.
"""

import pypdfium2 as pdfium

# Generous for real documents: letter at 200 dpi is ~3.7M pixels, so this only
# kicks in for pages more than ~13x that area.
MAX_RENDER_PIXELS = 50_000_000


class Cancelled(Exception):
    """Raised when a cancel Event is set while rendering pages."""


def page_count(pdf_bytes: bytes) -> int:
    """Number of pages in a (decrypted) PDF, without rendering any of them."""
    doc = pdfium.PdfDocument(pdf_bytes)
    try:
        return len(doc)
    finally:
        doc.close()


def clamped_scale(
    width_pt: float, height_pt: float, dpi: int, max_pixels: int | None = None
) -> float:
    """Return the pdfium render scale for ``dpi``, capped to the pixel budget."""
    if max_pixels is None:
        max_pixels = MAX_RENDER_PIXELS
    scale = dpi / 72.0
    pixels = (width_pt * scale) * (height_pt * scale)
    if pixels > max_pixels:
        scale *= (max_pixels / pixels) ** 0.5
    return scale

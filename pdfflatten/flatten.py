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

from .render import Cancelled, clamped_scale

FAX_DPI = 200
# Common fax APIs cap uploads around 30 MB; stay comfortably under that.
DEFAULT_MAX_BYTES = 25 * 1024 * 1024
# Resolutions to fall back to (descending) if the file is still too large.
_DPI_LADDER = (200, 150, 120, 100)


def _render_pages(
    pdf_bytes: bytes, dpi: int, *, progress=None, cancel=None, phase: str = "Flattening"
) -> list[bytes]:
    """Render every page to a 1-bit PNG at ``dpi``, returning the PNG bytes.

    Calls ``progress(current, total, phase)`` after each page and raises
    :class:`~pdfflatten.render.Cancelled` if ``cancel`` is set at a page boundary.
    """
    doc = pdfium.PdfDocument(pdf_bytes)
    images: list[bytes] = []
    try:
        total = len(doc)
        for index, page in enumerate(doc, start=1):
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            # Cap the render to the pixel budget so a hostile page size can't
            # force a huge allocation; the effective DPI drops instead.
            scale = clamped_scale(*page.get_size(), dpi)
            effective_dpi = max(1, round(scale * 72))
            bitmap = page.render(scale=scale, grayscale=True)
            gray = bitmap.to_pil().convert("L")
            bitmap.close()
            # Threshold to bilevel (no dithering) — crisp text and best G4 compression.
            bw = gray.convert("1", dither=Image.NONE)
            buf = io.BytesIO()
            # Embed the DPI so img2pdf sizes each page to its true physical size.
            bw.save(buf, format="PNG", dpi=(effective_dpi, effective_dpi))
            images.append(buf.getvalue())
            page.close()
            if progress is not None:
                progress(index, total, phase)
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
    pdf_bytes: bytes,
    dpi: int = FAX_DPI,
    max_bytes: int | None = DEFAULT_MAX_BYTES,
    *,
    progress=None,
    cancel=None,
) -> bytes:
    """Rasterize ``pdf_bytes`` to a flat, fax-ready, bitonal PDF.

    The result has no forms, annotations, transparency, or interactivity. Output
    is rendered at ``dpi``; if ``max_bytes`` is set and the file exceeds it, the
    resolution is reduced step by step until it fits (or the lowest is reached).

    ``progress(current, total, phase)`` is called once per page; the first pass
    reports phase ``"Flattening"`` and any size-reduction re-render reports
    ``"Reducing size"``. ``cancel`` is a ``threading.Event`` checked at each page
    boundary; if set, :class:`~pdfflatten.render.Cancelled` is raised and nothing
    is returned.
    """
    candidate_dpis = (dpi, *(d for d in _DPI_LADDER if d < dpi))
    result = b""
    for pass_index, candidate_dpi in enumerate(candidate_dpis):
        phase = "Flattening" if pass_index == 0 else "Reducing size"
        result = _assemble(
            _render_pages(pdf_bytes, candidate_dpi, progress=progress, cancel=cancel, phase=phase)
        )
        if max_bytes is None or len(result) <= max_bytes:
            return result
    return result  # smallest we could produce, even if still over the limit

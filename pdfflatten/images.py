"""Convert a PDF into one JPG image per page (a fallback when a PDF won't send).

Each page is rendered to a grayscale JPEG sized for faxing. If a page's JPEG
exceeds a size limit, quality and then resolution are reduced until it fits, so
every image stays under the fax service's per-file cap.
"""

import io

import pypdfium2 as pdfium
from PIL import Image

from .render import Cancelled, clamped_scale

JPG_DPI = 200
# Keep each image comfortably under common 30 MB fax limits.
DEFAULT_MAX_BYTES = 25 * 1024 * 1024
_DPI_LADDER = (200, 150, 120, 100)
_QUALITY_LADDER = (85, 70, 55)


def _encode(pil_image: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _page_to_jpg(page, dpi: int, max_bytes: int | None) -> bytes:
    """Render one page to a grayscale JPEG, shrinking until it fits max_bytes."""
    candidate_dpis = (dpi, *(d for d in _DPI_LADDER if d < dpi))
    data = b""
    for candidate_dpi in candidate_dpis:
        # Cap the render to the pixel budget so a hostile page size can't
        # force a huge allocation; the effective DPI drops instead.
        scale = clamped_scale(*page.get_size(), candidate_dpi)
        bitmap = page.render(scale=scale, grayscale=True)
        pil_image = bitmap.to_pil().convert("L")
        bitmap.close()
        for quality in _QUALITY_LADDER:
            data = _encode(pil_image, quality)
            if max_bytes is None or len(data) <= max_bytes:
                return data
    return data  # smallest we could produce, even if still over the limit


def pdf_to_jpegs(
    pdf_bytes: bytes,
    dpi: int = JPG_DPI,
    max_bytes: int | None = DEFAULT_MAX_BYTES,
    *,
    progress=None,
    cancel=None,
) -> list[bytes]:
    """Return a list of JPEG byte strings, one per page of ``pdf_bytes``.

    ``progress(current, total, "Converting to JPG")`` is called once per page.
    ``cancel`` is a ``threading.Event`` checked at each page boundary; if set,
    :class:`~pdfflatten.render.Cancelled` is raised.
    """
    doc = pdfium.PdfDocument(pdf_bytes)
    images: list[bytes] = []
    try:
        total = len(doc)
        for index, page in enumerate(doc, start=1):
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            images.append(_page_to_jpg(page, dpi, max_bytes))
            page.close()
            if progress is not None:
                progress(index, total, "Converting to JPG")
    finally:
        doc.close()
    return images

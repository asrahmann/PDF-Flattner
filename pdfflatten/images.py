"""Convert a PDF into one JPG image per page (a fallback when a PDF won't send).

Each page is rendered to a grayscale JPEG sized for faxing. If a page's JPEG
exceeds a size limit, quality and then resolution are reduced until it fits, so
every image stays under the fax service's per-file cap.
"""

import io

import pypdfium2 as pdfium
from PIL import Image

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
        scale = candidate_dpi / 72.0
        pil_image = page.render(scale=scale, grayscale=True).to_pil().convert("L")
        for quality in _QUALITY_LADDER:
            data = _encode(pil_image, quality)
            if max_bytes is None or len(data) <= max_bytes:
                return data
    return data  # smallest we could produce, even if still over the limit


def pdf_to_jpegs(
    pdf_bytes: bytes, dpi: int = JPG_DPI, max_bytes: int | None = DEFAULT_MAX_BYTES
) -> list[bytes]:
    """Return a list of JPEG byte strings, one per page of ``pdf_bytes``."""
    doc = pdfium.PdfDocument(pdf_bytes)
    images: list[bytes] = []
    try:
        for page in doc:
            images.append(_page_to_jpg(page, dpi, max_bytes))
            page.close()
    finally:
        doc.close()
    return images

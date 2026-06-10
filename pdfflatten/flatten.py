"""Flatten a PDF by rasterizing each page to a grayscale image at fax resolution."""

import io

import img2pdf
import pikepdf
import pypdfium2 as pdfium

FAX_DPI = 200


def flatten_pdf_bytes(pdf_bytes: bytes, dpi: int = FAX_DPI) -> bytes:
    """Render every page of ``pdf_bytes`` to a grayscale image and rebuild a flat PDF.

    The result has no forms, annotations, transparency, or interactivity — only
    one image per page — and is linearized for reliable fax-API ingestion.
    """
    doc = pdfium.PdfDocument(pdf_bytes)
    scale = dpi / 72.0
    page_images: list[bytes] = []
    page_layouts = []
    try:
        for page in doc:
            bitmap = page.render(scale=scale, grayscale=True)
            pil_image = bitmap.to_pil().convert("L")
            jpg = io.BytesIO()
            pil_image.save(jpg, format="JPEG", quality=85)
            page_images.append(jpg.getvalue())
            # Preserve physical page size (points → inches) for correct fax dimensions.
            width_pt, height_pt = page.get_size()
            page_layouts.append(
                img2pdf.get_layout_fun(
                    (img2pdf.in_to_pt(width_pt / 72.0), img2pdf.in_to_pt(height_pt / 72.0))
                )
            )
            page.close()
    finally:
        doc.close()

    layout_fun = page_layouts[0] if page_layouts else None
    assembled = img2pdf.convert(page_images, layout_fun=layout_fun)

    # Linearize ("fast web view") for maximum fax-API compatibility.
    pdf = pikepdf.open(io.BytesIO(assembled))
    out = io.BytesIO()
    with pdf:
        pdf.save(out, linearize=True)
    return out.getvalue()

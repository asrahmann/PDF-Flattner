import io

import pikepdf
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def _base_pdf_bytes(text="Hello fax world"):
    """A simple 1-page PDF with some text."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buf.getvalue()


def _multi_page_pdf_bytes(pages=3):
    """A PDF with ``pages`` simple text pages."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for i in range(pages):
        c.drawString(72, 720, f"Page {i + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


def _form_pdf_bytes():
    """A 1-page PDF containing an interactive AcroForm text field."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 720, "Form below:")
    form = c.acroForm
    form.textfield(name="field1", x=72, y=680, width=200, height=20)
    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def base_pdf(tmp_path):
    p = tmp_path / "base.pdf"
    p.write_bytes(_base_pdf_bytes())
    return p


@pytest.fixture
def owner_encrypted_pdf(tmp_path):
    """Owner-restricted only: opens with empty password, has restrictions."""
    src = pikepdf.open(io.BytesIO(_base_pdf_bytes()))
    p = tmp_path / "owner.pdf"
    src.save(p, encryption=pikepdf.Encryption(owner="ownerpw", user="", R=4))
    return p


@pytest.fixture
def user_encrypted_pdf(tmp_path):
    """Requires the password 'secret' to open."""
    src = pikepdf.open(io.BytesIO(_base_pdf_bytes()))
    p = tmp_path / "user.pdf"
    src.save(p, encryption=pikepdf.Encryption(owner="ownerpw", user="secret", R=4))
    return p


@pytest.fixture
def multi_page_pdf(tmp_path):
    p = tmp_path / "multi.pdf"
    p.write_bytes(_multi_page_pdf_bytes())
    return p


@pytest.fixture
def form_pdf(tmp_path):
    p = tmp_path / "form.pdf"
    p.write_bytes(_form_pdf_bytes())
    return p

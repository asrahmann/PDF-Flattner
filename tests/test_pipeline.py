import pikepdf
import pytest

from pdfflatten.decrypt import PasswordRequired
from pdfflatten.pipeline import output_path_for, process_pdf


def test_output_path_basic(tmp_path):
    out = output_path_for(tmp_path / "invoice.pdf", tmp_path)
    assert out == tmp_path / "flattened-invoice.pdf"


def test_output_path_collision_increments(tmp_path):
    (tmp_path / "flattened-invoice.pdf").write_text("x")
    out = output_path_for(tmp_path / "invoice.pdf", tmp_path)
    assert out == tmp_path / "flattened-invoice-2.pdf"


def test_output_path_collision_second(tmp_path):
    (tmp_path / "flattened-invoice.pdf").write_text("x")
    (tmp_path / "flattened-invoice-2.pdf").write_text("x")
    out = output_path_for(tmp_path / "invoice.pdf", tmp_path)
    assert out == tmp_path / "flattened-invoice-3.pdf"


def test_process_writes_flat_unencrypted_file(owner_encrypted_pdf, tmp_path):
    out = process_pdf(owner_encrypted_pdf, output_dir=tmp_path)
    assert out.exists()
    assert out.name == "flattened-owner.pdf"
    pdf = pikepdf.open(out)
    assert not pdf.is_encrypted
    assert "/AcroForm" not in pdf.Root


def test_process_propagates_password_required(user_encrypted_pdf, tmp_path):
    with pytest.raises(PasswordRequired):
        process_pdf(user_encrypted_pdf, output_dir=tmp_path)


def test_process_decrypts_with_password(user_encrypted_pdf, tmp_path):
    out = process_pdf(user_encrypted_pdf, output_dir=tmp_path, password="secret")
    assert out.exists()
    assert not pikepdf.open(out).is_encrypted

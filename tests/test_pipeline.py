import sys
import threading

import pikepdf
import pytest

needs_symlinks = pytest.mark.skipif(
    sys.platform == "win32", reason="symlink creation needs privileges on Windows"
)

from pdfflatten.decrypt import PasswordRequired
from pdfflatten.pipeline import (
    flatten_decrypted,
    jpgs_from_decrypted,
    output_folder_for,
    output_path_for,
    process_pdf,
    process_pdf_to_jpgs,
)
from pdfflatten.render import Cancelled


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


def test_output_folder_basic(tmp_path):
    out = output_folder_for(tmp_path / "invoice.pdf", tmp_path)
    assert out == tmp_path / "invoice"


def test_output_folder_collision_increments(tmp_path):
    (tmp_path / "invoice").mkdir()
    out = output_folder_for(tmp_path / "invoice.pdf", tmp_path)
    assert out == tmp_path / "invoice-2"


def test_process_to_jpgs_creates_folder_with_page_images(base_pdf, tmp_path):
    folder = process_pdf_to_jpgs(base_pdf, output_dir=tmp_path)
    assert folder.is_dir()
    assert folder.name == "base"
    jpgs = sorted(folder.glob("*.jpg"))
    assert len(jpgs) == 1
    assert jpgs[0].name == "base-page-1.jpg"


def test_process_to_jpgs_decrypts_owner_restricted(owner_encrypted_pdf, tmp_path):
    folder = process_pdf_to_jpgs(owner_encrypted_pdf, output_dir=tmp_path)
    assert folder.is_dir()
    assert len(list(folder.glob("*.jpg"))) == 1


def test_process_to_jpgs_propagates_password_required(user_encrypted_pdf, tmp_path):
    with pytest.raises(PasswordRequired):
        process_pdf_to_jpgs(user_encrypted_pdf, output_dir=tmp_path)


def test_process_pdf_collision_writes_incremented_name(base_pdf, tmp_path):
    (tmp_path / "flattened-base.pdf").write_text("x")
    out = process_pdf(base_pdf, output_dir=tmp_path)
    assert out.name == "flattened-base-2.pdf"
    assert (tmp_path / "flattened-base.pdf").read_text() == "x"


@needs_symlinks
def test_process_pdf_does_not_write_through_dangling_symlink(base_pdf, tmp_path):
    # A dangling symlink at the predictable output name must not redirect the
    # write to its target — the name should be skipped like any collision.
    outdir = tmp_path / "out"
    outdir.mkdir()
    victim = tmp_path / "victim.pdf"
    (outdir / "flattened-base.pdf").symlink_to(victim)
    out = process_pdf(base_pdf, output_dir=outdir)
    assert not victim.exists()
    assert out.name == "flattened-base-2.pdf"


@needs_symlinks
def test_process_to_jpgs_skips_dangling_symlink_folder_name(base_pdf, tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    victim = tmp_path / "victim-folder"
    (outdir / "base").symlink_to(victim)
    folder = process_pdf_to_jpgs(base_pdf, output_dir=outdir)
    assert not victim.exists()
    assert folder.name == "base-2"


def test_flatten_decrypted_writes_file(base_pdf, tmp_path):
    out = flatten_decrypted(base_pdf.read_bytes(), base_pdf, tmp_path)
    assert out.exists()
    assert out.name == "flattened-base.pdf"


def test_flatten_decrypted_reports_progress(multi_page_pdf, tmp_path):
    calls = []
    flatten_decrypted(
        multi_page_pdf.read_bytes(),
        multi_page_pdf,
        tmp_path,
        progress=lambda cur, total, phase: calls.append(cur),
    )
    assert calls == [1, 2, 3]


def test_flatten_decrypted_cancel_writes_nothing(multi_page_pdf, tmp_path):
    cancel = threading.Event()
    cancel.set()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    with pytest.raises(Cancelled):
        flatten_decrypted(multi_page_pdf.read_bytes(), multi_page_pdf, out_dir, cancel=cancel)
    assert list(out_dir.iterdir()) == []


def test_jpgs_from_decrypted_writes_folder(multi_page_pdf, tmp_path):
    folder = jpgs_from_decrypted(multi_page_pdf.read_bytes(), multi_page_pdf, tmp_path)
    assert folder.is_dir()
    assert len(list(folder.glob("*.jpg"))) == 3


def test_jpgs_from_decrypted_cancel_creates_no_folder(multi_page_pdf, tmp_path):
    # The output folder is created only after every page has rendered, so a
    # cancel mid-render must leave the output dir with no folder at all.
    cancel = threading.Event()
    cancel.set()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    with pytest.raises(Cancelled):
        jpgs_from_decrypted(multi_page_pdf.read_bytes(), multi_page_pdf, out_dir, cancel=cancel)
    assert list(out_dir.iterdir()) == []

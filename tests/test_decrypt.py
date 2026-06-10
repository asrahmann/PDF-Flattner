import io

import pikepdf
import pytest

from pdfflatten.decrypt import PasswordRequired, decrypt_to_bytes


def test_plain_pdf_passes_through(base_pdf):
    data = decrypt_to_bytes(base_pdf)
    out = pikepdf.open(io.BytesIO(data))
    assert not out.is_encrypted


def test_owner_restricted_is_decrypted_without_password(owner_encrypted_pdf):
    data = decrypt_to_bytes(owner_encrypted_pdf)
    out = pikepdf.open(io.BytesIO(data))
    assert not out.is_encrypted


def test_user_password_required_raises(user_encrypted_pdf):
    with pytest.raises(PasswordRequired):
        decrypt_to_bytes(user_encrypted_pdf)


def test_user_password_correct_decrypts(user_encrypted_pdf):
    data = decrypt_to_bytes(user_encrypted_pdf, password="secret")
    out = pikepdf.open(io.BytesIO(data))
    assert not out.is_encrypted


def test_user_password_wrong_raises(user_encrypted_pdf):
    with pytest.raises(PasswordRequired):
        decrypt_to_bytes(user_encrypted_pdf, password="wrong")

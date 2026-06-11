from pathlib import Path

LICENSE_PATH = Path(__file__).resolve().parents[1] / "LICENSE"


def test_license_exists():
    assert LICENSE_PATH.is_file()


def test_license_is_mit_with_copyright():
    text = LICENSE_PATH.read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Copyright (c) 2026 Ahmedur Rahman" in text
    # The attribution clause that makes credit a condition of use:
    assert "above copyright notice and this permission notice shall be included" in text
    # Guard against a truncated file: the warranty/liability paragraph must be present.
    assert "WITHOUT WARRANTY OF ANY KIND" in text

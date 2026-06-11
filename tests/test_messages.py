from pdfflatten.messages import (
    format_summary,
    split_by_extension,
    unsupported_message,
)


def test_split_by_extension_mixed_case_insensitive():
    pdfs, others = split_by_extension(["a.pdf", "b.txt", "c.PDF", "d.jpg"])
    assert pdfs == ["a.pdf", "c.PDF"]
    assert others == ["b.txt", "d.jpg"]


def test_split_by_extension_empty():
    assert split_by_extension([]) == ([], [])


def test_unsupported_message_names_basenames():
    msg = unsupported_message(["/x/notes.txt", "/y/photo.jpg"])
    assert msg == "Not a PDF (PDF only): notes.txt, photo.jpg"


def test_format_summary_only_saved_is_green():
    msg, colour = format_summary(["flattened-a.pdf"], [], [], 0, "pdf")
    assert msg == "✓ Saved PDF(s) on Desktop:\nflattened-a.pdf"
    assert colour == "#070"


def test_format_summary_mixed_has_three_sections_in_order_and_is_red():
    msg, colour = format_summary(
        ["flattened-report.pdf"],
        ["notes.txt"],
        ["scan.pdf — could not read this PDF (it may be damaged)"],
        0,
        "pdf",
    )
    assert colour == "#b00"
    assert "✓ Saved PDF(s) on Desktop:\nflattened-report.pdf" in msg
    assert "⚠ Skipped (not a PDF):\nnotes.txt" in msg
    assert "✗ Failed:\nscan.pdf — could not read this PDF (it may be damaged)" in msg
    assert msg.index("✓ Saved") < msg.index("⚠ Skipped") < msg.index("✗ Failed")


def test_format_summary_skipped_only_is_amber():
    msg, colour = format_summary([], ["notes.txt"], [], 0, "pdf")
    assert msg == "⚠ Skipped (not a PDF):\nnotes.txt"
    assert colour == "#b80"
    assert "✗ Failed" not in msg


def test_format_summary_cancelled_counts_as_failure():
    msg, colour = format_summary(["flattened-a.pdf"], [], [], 2, "jpg")
    assert colour == "#b00"
    assert "JPG folder(s) on Desktop" in msg
    assert "2 file(s) cancelled" in msg


def test_format_summary_empty_is_nothing_to_do():
    msg, colour = format_summary([], [], [], 0, "pdf")
    assert msg == "Nothing to do."
    assert colour == "#444"


def test_disclaimer_text_has_key_clauses():
    from pdfflatten.messages import DISCLAIMER_TEXT

    text = DISCLAIMER_TEXT.lower()
    assert "as is" in text
    assert "at your own risk" in text
    assert "not be liable" in text
    assert "ahmedur rahman" in text
    assert "ok to accept" in text
    assert "cancel to exit" in text

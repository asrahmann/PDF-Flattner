"""User-facing result messages for the GUI, with no Tk dependency.

Kept separate from ``gui.py`` so the message/colour logic can be unit-tested on
any machine (the GUI itself needs a display).
"""

from pathlib import Path

# Status colours used by the GUI label.
GREEN = "#070"
AMBER = "#b80"
RED = "#b00"
NEUTRAL = "#444"


def split_by_extension(paths, ext: str = ".pdf") -> tuple[list, list]:
    """Split ``paths`` into (matching, others) by file extension, case-insensitively."""
    ext = ext.lower()
    matching, others = [], []
    for p in paths:
        (matching if str(p).lower().endswith(ext) else others).append(p)
    return matching, others


def unsupported_message(non_pdfs) -> str:
    """Red pre-batch message naming the non-PDF files that were given."""
    names = ", ".join(Path(p).name for p in non_pdfs)
    return f"Not a PDF (PDF only): {names}"


def format_summary(done, skipped, failed, cancelled: int, mode: str) -> tuple[str, str]:
    """Return (message, colour) summarising a finished batch.

    Sections appear in this order, each omitted when empty: saved, skipped
    (not a PDF), failed. A non-zero ``cancelled`` count is shown as a failure
    line. Colour: green if only saved; amber if skips but no failures; red if
    anything failed or was cancelled; neutral when there is nothing to report.
    """
    label = "JPG folder(s) on Desktop" if mode == "jpg" else "PDF(s) on Desktop"
    failed_lines = list(failed)
    if cancelled > 0:
        failed_lines.append(f"{cancelled} file(s) cancelled")

    sections = []
    if done:
        sections.append(f"✓ Saved {label}:\n" + "\n".join(done))
    if skipped:
        sections.append("⚠ Skipped (not a PDF):\n" + "\n".join(skipped))
    if failed_lines:
        sections.append("✗ Failed:\n" + "\n".join(failed_lines))

    if not sections:
        return "Nothing to do.", NEUTRAL
    if failed_lines:
        colour = RED
    elif skipped:
        colour = AMBER
    else:
        colour = GREEN
    return "\n\n".join(sections), colour


# Shown (every launch) before the main window; the user must accept to continue.
DISCLAIMER_TEXT = (
    'PDF Flatten & Decrypt\n\n'
    'This software is provided "as is", without warranty of any kind, express '
    "or implied, including but not limited to the warranties of "
    "merchantability, fitness for a particular purpose, and non-infringement.\n\n"
    "By clicking OK and using this application, you acknowledge that you use it "
    "entirely at your own risk, and that the developer (Ahmedur Rahman) shall "
    "not be liable for any claim, loss, or damage of any kind — including data "
    "loss or errors in processed files — arising from or in connection with the "
    "software or its use.\n\n"
    "Click OK to accept and continue, or Cancel to exit."
)

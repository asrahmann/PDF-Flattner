"""GUI smoke tests that need a real display.

These construct actual Tk widgets, so they catch widget-option errors that a
plain ``import pdfflatten.gui`` cannot (the error only surfaces when the widget
is built). On a headless machine ``tk.Tk()`` fails and the test skips.
"""

import tkinter as tk

import pytest


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:  # no display (headless CI / dev box)
        pytest.skip(f"no display available for Tk: {exc}")
    root.withdraw()
    yield root
    root.destroy()


def test_progress_dialog_constructs_and_updates(tk_root):
    # Regression: a tuple passed to a widget's pady option (vs. pack's pady)
    # raised TclError mid-construction, leaving a blank "Working…" window.
    from pdfflatten.gui import ProgressDialog

    dialog = ProgressDialog(tk_root, on_cancel=lambda: None)
    dialog.start_file("sample.pdf", 1, 3)
    dialog.update(2, 3, "Flattening")
    dialog.close()

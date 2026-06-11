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


def _make_app_or_skip():
    try:
        from pdfflatten.gui import App

        return App()
    except (tk.TclError, RuntimeError) as exc:  # no display / no tkdnd
        pytest.skip(f"no display available for Tk: {exc}")


def test_run_cancel_exits_without_mainloop(monkeypatch):
    app = _make_app_or_skip()
    monkeypatch.setattr("pdfflatten.gui.messagebox.askokcancel", lambda *a, **k: False)
    entered = []
    monkeypatch.setattr(app.root, "mainloop", lambda: entered.append(True))
    app.run()
    assert entered == []  # Cancel: the main loop must never start


def test_run_ok_enters_mainloop(monkeypatch):
    app = _make_app_or_skip()
    monkeypatch.setattr("pdfflatten.gui.messagebox.askokcancel", lambda *a, **k: True)
    entered = []
    monkeypatch.setattr(app.root, "mainloop", lambda: entered.append(True))
    try:
        app.run()
        assert entered == [True]  # OK: the main loop runs once
    finally:
        try:
            app.root.destroy()
        except tk.TclError:
            pass

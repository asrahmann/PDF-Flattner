"""A minimal Tkinter GUI: drop PDFs, prompt for password if needed, save to Desktop.

Rendering runs on a worker thread; the main thread owns every widget and drains
a queue via ``after``. A per-page progress bar and Cancel button keep the window
responsive on large documents.
"""

import queue
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from . import __version__
from .decrypt import PasswordRequired, decrypt_to_bytes
from .desktop import desktop_dir
from .pipeline import flatten_decrypted, jpgs_from_decrypted
from .render import Cancelled, page_count
from .messages import format_summary, split_by_extension, unsupported_message

DEVELOPER = "Ahmedur Rahman"
DEVELOPER_EMAIL = "Ahmedur.Rahman@cloudcodelabs.com"

# A document this long is worth a heads-up: it may take a while, and the user's
# fax plan must support sending this many pages. Advisory only — never blocks.
FAX_PLAN_PAGE_WARNING = 50


class ProgressDialog:
    """A modal progress window that persists across a batch run."""

    def __init__(self, root, on_cancel) -> None:
        self.top = tk.Toplevel(root)
        self.top.title("Working…")
        self.top.transient(root)
        self.top.resizable(False, False)
        # Closing the window or Cancel both request cancellation.
        self.top.protocol("WM_DELETE_WINDOW", on_cancel)

        self._file = tk.Label(self.top, text="Preparing…", padx=24)
        self._file.pack(pady=(16, 4))
        self._phase = tk.Label(self.top, text="", fg="#444", padx=24)
        self._phase.pack()
        self._bar = ttk.Progressbar(self.top, length=340, mode="determinate")
        self._bar.pack(padx=24, pady=12)
        tk.Button(self.top, text="Cancel", width=12, command=on_cancel).pack(pady=(0, 14))

        self.top.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() - self.top.winfo_width()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - self.top.winfo_height()) // 2
        self.top.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.top.grab_set()

    def start_file(self, name: str, index: int, total: int) -> None:
        self._file.config(text=f"File {index} of {total} — {name}")
        self._phase.config(text="Preparing…")
        self._bar.config(value=0, maximum=100)
        self.top.update_idletasks()

    def update(self, current: int, total: int, phase: str) -> None:
        self._bar.config(maximum=total, value=current)
        self._phase.config(text=f"{phase} — page {current} of {total}")
        self.top.update_idletasks()

    def close(self) -> None:
        self.top.grab_release()
        self.top.destroy()


class App:
    def __init__(self) -> None:
        self.root = TkinterDnD.Tk()
        self.root.title("PDF Flatten & Decrypt")
        self.root.geometry("460x300")
        self.root.minsize(420, 260)

        tk.Label(
            self.root,
            text="Drop PDF files here\nto decrypt & flatten for faxing",
            font=("Helvetica", 15),
            justify="center",
        ).pack(expand=True, fill="both", padx=20, pady=(20, 5))

        buttons = tk.Frame(self.root)
        buttons.pack(pady=5)
        tk.Button(buttons, text="Flatten to PDF…", command=self._choose_pdf).pack(side="left", padx=4)
        tk.Button(buttons, text="Convert to JPG…", command=self._choose_jpg).pack(side="left", padx=4)
        tk.Button(buttons, text="About", command=self._about).pack(side="left", padx=4)

        self.status = tk.Label(
            self.root,
            text="Drop a PDF and choose Flatten or JPG.\nEverything saves to your Desktop.",
            fg="#444",
            wraplength=420,
            justify="center",
        )
        self.status.pack(pady=10)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._on_drop)

    def _choose_pdf(self) -> None:
        self._handle(self._ask_files(), mode="pdf")

    def _choose_jpg(self) -> None:
        self._handle(self._ask_files(), mode="jpg")

    def _ask_files(self):
        return list(
            filedialog.askopenfilenames(
                title="Choose PDF(s)", filetypes=[("PDF files", "*.pdf")]
            )
        )

    def _on_drop(self, event) -> None:
        # tkinterdnd2 returns a brace/space-delimited list; splitlist handles it.
        paths = list(self.root.tk.splitlist(event.data))
        pdfs, non_pdfs = split_by_extension(paths)
        if not pdfs:
            self._set(
                unsupported_message(non_pdfs) if non_pdfs else "Please drop PDF files (.pdf).",
                "#b00",
            )
            return
        mode = self._ask_mode()
        if mode is None:  # user cancelled
            return
        # Pass the full list (not just pdfs): _handle re-splits to populate _skipped.
        self._handle(paths, mode=mode)

    def _ask_mode(self):
        """Modal popup: return 'pdf', 'jpg', or None if cancelled."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Choose action")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        result = {"mode": None}

        tk.Label(
            dialog,
            text="What should I do with the dropped file(s)?",
            padx=20,
            pady=14,
        ).pack()

        def pick(mode):
            result["mode"] = mode
            dialog.destroy()

        row = tk.Frame(dialog)
        row.pack(padx=20, pady=(0, 10))
        tk.Button(row, text="Flatten to PDF", width=16, command=lambda: pick("pdf")).pack(side="left", padx=5)
        tk.Button(row, text="Convert to JPG", width=16, command=lambda: pick("jpg")).pack(side="left", padx=5)
        tk.Button(dialog, text="Cancel", command=lambda: pick(None)).pack(pady=(0, 12))

        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result["mode"]

    def _handle(self, paths, mode: str) -> None:
        pdfs, non_pdfs = split_by_extension(paths)
        if not pdfs:
            self._set(
                unsupported_message(non_pdfs) if non_pdfs else "Please choose PDF files (.pdf).",
                "#b00",
            )
            return
        # Batch run state. Driven by after()-callbacks so the UI never blocks.
        self._mode = mode
        self._pdfs = pdfs
        self._index = 0
        self._done: list[str] = []
        self._skipped: list[str] = [Path(p).name for p in non_pdfs]
        self._failed: list[str] = []
        self._cancelled = False
        self._cancel = threading.Event()
        self._queue: queue.Queue = queue.Queue()
        self._progress = ProgressDialog(self.root, on_cancel=self._request_cancel)
        self._next_file()

    def _request_cancel(self) -> None:
        # Cooperative: the worker stops at the next page boundary.
        self._cancelled = True
        self._cancel.set()

    def _next_file(self) -> None:
        if self._cancelled or self._index >= len(self._pdfs):
            self._finish_batch()
            return
        path = Path(self._pdfs[self._index])
        self._progress.start_file(path.name, self._index + 1, len(self._pdfs))

        decrypted = self._decrypt_with_password(path)
        if decrypted is None:  # failure reason already recorded by the helper
            self._index += 1
            self._next_file()
            return

        try:
            pages = page_count(decrypted)
        except Exception:  # noqa: BLE001 - a bad count must not block processing
            pages = 0
        if pages >= FAX_PLAN_PAGE_WARNING and not self._confirm_large(path, pages):
            self._failed.append(f"{path.name} — skipped (chose not to continue)")
            self._index += 1
            self._next_file()
            return

        worker = threading.Thread(
            target=self._worker, args=(decrypted, path, self._mode), daemon=True
        )
        worker.start()
        self.root.after(100, self._poll)

    def _decrypt_with_password(self, path: Path):
        """Decrypt on the main thread, prompting up to 3 times.

        Returns the decrypted bytes, or None after recording a single plain
        reason in ``self._failed`` (unreadable PDF, no password, or wrong one).
        """
        password = ""
        for _ in range(3):
            try:
                return decrypt_to_bytes(path, password=password)
            except PasswordRequired:
                password = simpledialog.askstring(
                    "Password required",
                    f"Enter the password to open:\n{path.name}",
                    show="*",
                    parent=self.root,
                )
                if password is None:  # user cancelled the prompt
                    self._failed.append(f"{path.name} — password required (not provided)")
                    return None
            except Exception:  # noqa: BLE001 - any open failure means we can't read it
                self._failed.append(f"{path.name} — could not read this PDF (it may be damaged)")
                return None
        self._failed.append(f"{path.name} — incorrect password")
        return None

    def _confirm_large(self, path: Path, pages: int) -> bool:
        return messagebox.askokcancel(
            "Large document",
            f"{path.name} has {pages} pages.\n\n"
            "Processing this many pages may take some time, and your fax service "
            "plan must support sending a document this long.\n\n"
            "Continue?",
            parent=self.root,
        )

    def _worker(self, decrypted: bytes, path: Path, mode: str) -> None:
        """Runs on a worker thread. Touches no widgets — only the queue."""
        def progress(current, total, phase):
            self._queue.put(("progress", current, total, phase))

        try:
            processor = jpgs_from_decrypted if mode == "jpg" else flatten_decrypted
            out = processor(decrypted, path, desktop_dir(), progress=progress, cancel=self._cancel)
            self._queue.put(("done", out))
        except Cancelled:
            self._queue.put(("cancelled",))
        except Exception as exc:  # noqa: BLE001 - report any failure to the user
            self._queue.put(("error", exc))

    def _poll(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, current, total, phase = msg
                    self._progress.update(current, total, phase)
                elif kind == "done":
                    self._done.append(msg[1].name)
                    self._advance()
                    return
                elif kind == "cancelled":
                    self._cancelled = True
                    self._advance()
                    return
                elif kind == "error":
                    name = Path(self._pdfs[self._index]).name
                    self._failed.append(f"{name}: {msg[1]}")
                    self._advance()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _advance(self) -> None:
        self._index += 1
        self._next_file()

    def _finish_batch(self) -> None:
        self._progress.close()
        cancelled = len(self._pdfs) - self._index if self._cancelled else 0
        message, colour = format_summary(
            self._done, self._skipped, self._failed, cancelled, self._mode
        )
        self._set(message, colour)

    def _about(self) -> None:
        messagebox.showinfo(
            "About PDF Flatten & Decrypt",
            "PDF Flatten & Decrypt\n"
            f"Version {__version__}\n\n"
            "A secure, offline tool to decrypt and flatten PDF files.\n"
            "All processing happens on your computer — nothing is uploaded.\n\n"
            f"Developed by {DEVELOPER}\n"
            f"{DEVELOPER_EMAIL}",
            parent=self.root,
        )

    def _set(self, text: str, color: str = "#444") -> None:
        self.status.config(text=text, fg=color)
        self.root.update_idletasks()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    App().run()

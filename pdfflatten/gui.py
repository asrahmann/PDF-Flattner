"""A minimal Tkinter GUI: drop PDFs, prompt for password if needed, save to Desktop."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from tkinterdnd2 import DND_FILES, TkinterDnD

from . import __version__
from .decrypt import PasswordRequired
from .desktop import desktop_dir
from .pipeline import process_pdf, process_pdf_to_jpgs

DEVELOPER = "Ahmedur Rahman"
DEVELOPER_EMAIL = "Ahmedur.Rahman@cloudcodelabs.com"


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
        if not any(str(p).lower().endswith(".pdf") for p in paths):
            self._set("Please drop PDF files (.pdf).", "#b00")
            return
        mode = self._ask_mode()
        if mode is None:  # user cancelled
            return
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
        pdfs = [p for p in paths if str(p).lower().endswith(".pdf")]
        if not pdfs:
            self._set("Please choose PDF files (.pdf).", "#b00")
            return
        done, failed = [], []
        for p in pdfs:
            try:
                out = self._process_one(Path(p), mode)
                if out is None:
                    failed.append(f"{Path(p).name} (skipped)")
                else:
                    done.append(out.name)
            except Exception as exc:  # noqa: BLE001 - surface any error to the user
                failed.append(f"{Path(p).name}: {exc}")
        label = "JPG folder(s) on Desktop" if mode == "jpg" else "PDF(s) on Desktop"
        msg = ""
        if done:
            msg += f"✓ Saved {label}:\n" + "\n".join(done)
        if failed:
            msg += ("\n\n" if done else "") + "✗ Problems:\n" + "\n".join(failed)
        self._set(msg, "#070" if not failed else "#b00")

    def _process_one(self, path: Path, mode: str):
        """Process one file, prompting for a password up to 3 times if needed."""
        processor = process_pdf_to_jpgs if mode == "jpg" else process_pdf
        password = ""
        for _ in range(3):
            try:
                return processor(path, output_dir=desktop_dir(), password=password)
            except PasswordRequired:
                password = simpledialog.askstring(
                    "Password required",
                    f"Enter the password to open:\n{path.name}",
                    show="*",
                    parent=self.root,
                )
                if password is None:  # user cancelled
                    return None
        raise PasswordRequired("incorrect password")

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

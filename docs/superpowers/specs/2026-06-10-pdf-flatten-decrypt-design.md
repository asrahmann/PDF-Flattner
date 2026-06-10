# PDF Flatten & Decrypt — Design Spec

**Date:** 2026-06-10
**Status:** Approved pending review

## Purpose

A small, portable desktop tool that takes a PDF, **decrypts it** (removes
encryption/password protection and owner restrictions) and **flattens it**
(removes all interactive/form/transparency content), producing a clean PDF that
can be reliably sent through the Vitelity fax API. Vitelity's fax API does not
accept encrypted PDFs and needs flattened files.

Everything runs **locally with zero network calls** — important because the
recipient works in a healthcare setting and the PDFs may contain PHI. No data
ever leaves the machine.

## Users & environment

- **Operator:** one person, likely on **Windows** (possibly Mac), in a
  healthcare setting.
- **Machine assumptions:** potentially locked down. **No installer, no admin
  rights** — the app must be a portable file they can double-click and run.
- They need the simplest possible experience: flatten + decrypt for faxing.
  Nothing more.

## Core decision: single rasterize-flatten path

Because the destination is a **fax** (an inherently image-based, ~200 dpi,
typically black-and-white medium), flattening by rasterizing each page to an
image is not a compromise — it is the ideal, most fax-compatible output. This
lets us collapse to **one processing path** with no modes or toggles:

```
decrypt  →  render each page to image (fax resolution)  →  rebuild as clean PDF
```

This guarantees the output has no forms, annotations, transparency, JavaScript,
or encryption — exactly what the fax API wants.

## User experience

1. Double-click the app → one small window opens.
2. **Drag a PDF (or several) onto the window**, or click "Choose file…".
3. If a file needs an **open password**, the app prompts for it. If a file is
   only **owner-restricted** (no-print / no-copy / no-edit), it is handled
   silently with no prompt.
4. The app writes a clean copy next to the original, suffixed `-flat`
   (e.g. `invoice.pdf` → `invoice-flat.pdf`).
5. A clear "✓ Done — saved to <path>" (or a plain error message) is shown.

One window. No menus, no settings, no configuration.

## Processing pipeline

For each input PDF:

1. **Decrypt / unlock**
   - Open the file. If encrypted with only an *owner* password (permission
     restrictions), open with an empty password and strip the restrictions.
   - If the file requires a *user* password to open, prompt the operator for it
     and retry. Save the fully decrypted content.
2. **Flatten by rasterizing**
   - Render every page to a raster image at fax resolution (target ~200 dpi,
     grayscale or 1-bit black-and-white to keep file size small).
   - Reassemble the images into a new PDF, one image per page, preserving page
     size/orientation.
3. **Output**
   - Save a linearized ("fast web view") PDF — a format fax APIs accept
     reliably — next to the source as `<name>-flat.pdf`.

## Technology

- **Language:** Python 3.12.
- **Decryption / unlock:** `pikepdf` (built on QPDF) — robust handling of
  real-world encrypted PDFs; permissively licensed.
- **Rendering / rasterization:** `pypdfium2` (Google PDFium) — permissively
  licensed, fast, no AGPL obligations.
- **PDF assembly:** `img2pdf` / `pikepdf` for building the final PDF from page
  images and linearizing.
- **GUI:** lightweight **Tkinter** (bundled with Python) plus `tkinterdnd2` for
  drag-and-drop. Chosen for the **smallest bundle size and best chance of
  running cleanly on a locked-down machine** — a heavier UI toolkit (e.g. Qt)
  produces a 4–5× larger file and a bigger antivirus surface.
- **Packaging:** **PyInstaller** producing a **portable build** (no installer,
  no admin). A single-file `.exe` is preferred for ease of handoff, with a
  folder ("onedir") build as a fallback if antivirus flags the single file.

## Distribution & the locked-down-machine risk

The biggest unknown is whether *any* unsigned executable will run on the
recipient's machine (application whitelisting, antivirus, etc.).

**De-risk first:** before building the full app, produce a tiny throwaway
portable `.exe` for the recipient to double-click.
- If it runs → the real app will run; proceed unsigned ($0).
- If it is blocked → we know we need code signing (Apple Developer $99/yr;
  Windows cert ~$200–400/yr) and/or IT involvement *before* investing further.

Code signing can be added later as a pure packaging step without changing any
app code.

## Testing

- **Unit/integration tests** on the pipeline using sample PDFs:
  - an owner-restricted PDF (permissions stripped, no prompt),
  - a user-password PDF (decrypts with correct password, fails clearly with
    wrong one),
  - a PDF with form fields/annotations (output has none),
  - a normal unencrypted PDF (still flattened and re-saved).
- Verify output PDFs are unencrypted, contain no interactive content, and open
  correctly.
- Manual smoke test of the GUI (drag-drop, password prompt, success/error
  display).

## Explicitly out of scope (YAGNI)

- No direct Vitelity API integration — the app only produces the clean file;
  faxing is done separately.
- No watch-folder / batch-automation mode.
- No settings, profiles, or configuration UI.
- No cloud, telemetry, or any network connection whatsoever.
```

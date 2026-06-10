# PDF Flatten & Decrypt

A small, **offline** desktop tool, developed as a **secure way to flatten PDF
files**. It decrypts and flattens PDFs so they can be sent through a fax API.
Everything runs locally — **no data ever leaves your computer**.

## What it does

Drop a PDF in, and it:

1. **Decrypts** it — removes password protection and owner restrictions
   (no-print / no-copy / no-edit). You're prompted for a password only if the
   file needs one to open.
2. **Flattens** it — rasterizes every page so there are no forms, annotations,
   transparency, or interactive content left. This is exactly what fax APIs
   require, and since a fax is an image anyway, nothing meaningful is lost.
3. **Saves** a copy named `flattened-<name>.pdf` to your **Desktop**.

## Download (no install)

Grab the latest portable `.exe` from the
[Releases page](https://github.com/asrahmann/PDF-Flattner/releases) — no
installer, no admin rights needed. Just double-click it.

> Windows may show a one-time SmartScreen prompt because the app isn't
> code-signed: click **More info → Run anyway**. (This is expected for an
> unsigned tool.)

## Use

1. Double-click the app.
2. Drag a PDF onto the window (or click **Choose file(s)…**).
3. If the PDF needs a password to open, enter it when asked.
4. Find `flattened-<name>.pdf` on your **Desktop**, ready to fax.

## Run from source

```bash
python3 -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python app.py        # launch the app
pytest               # run the tests
```

## Build the portable executable

The Windows `.exe` is built automatically by GitHub Actions (see
`.github/workflows/build.yml`) and attached to each tagged Release. To build
locally for your own platform:

```bash
pyinstaller --onefile --windowed --name "PDF-Flatten-Decrypt" \
  --collect-all tkinterdnd2 --collect-all pypdfium2 app.py
```

The result is in `dist/`. `--collect-all` bundles the `tkinterdnd2` and
`pypdfium2` native data files PyInstaller would otherwise miss.

## Privacy

There is **no network code anywhere** in this app. It cannot phone home, upload,
or transmit anything. All processing happens on your machine.

"""Orchestrate decrypt → flatten → save to a non-colliding Desktop path."""

from pathlib import Path

from .decrypt import decrypt_to_bytes
from .desktop import desktop_dir
from .flatten import flatten_pdf_bytes
from .images import pdf_to_jpegs


def _candidate_names(base: str, suffix: str = ""):
    """Yield ``base``, then ``base-2``, ``base-3``… (suffix appended to each)."""
    yield f"{base}{suffix}"
    counter = 2
    while True:
        yield f"{base}-{counter}{suffix}"
        counter += 1


def output_path_for(source, output_dir) -> Path:
    """Compute ``flattened-<stem>.pdf`` in output_dir, avoiding overwrite with -2, -3…"""
    output_dir = Path(output_dir)
    for name in _candidate_names(f"flattened-{Path(source).stem}", ".pdf"):
        candidate = output_dir / name
        if not candidate.exists():
            return candidate


def _write_new_file(output_dir: Path, names, data: bytes) -> Path:
    """Write ``data`` to the first name that can be created exclusively.

    ``open("xb")`` (O_CREAT|O_EXCL) refuses paths that already exist —
    including symlinks, even dangling ones — so a planted link at a
    predictable output name can never redirect the write to its target.
    """
    for name in names:
        path = output_dir / name
        try:
            with path.open("xb") as fh:
                fh.write(data)
        except FileExistsError:
            continue
        return path


def process_pdf(source, output_dir=None, password: str = "") -> Path:
    """Decrypt and flatten ``source``, write the result, and return its path.

    Raises :class:`~pdfflatten.decrypt.PasswordRequired` if the file needs an
    open password not supplied here.
    """
    source = Path(source)
    output_dir = Path(output_dir) if output_dir is not None else desktop_dir()
    decrypted = decrypt_to_bytes(source, password=password)
    flat = flatten_pdf_bytes(decrypted)
    return _write_new_file(output_dir, _candidate_names(f"flattened-{source.stem}", ".pdf"), flat)


def output_folder_for(source, output_dir) -> Path:
    """Compute a folder named after the source stem, avoiding collisions with -2, -3…"""
    output_dir = Path(output_dir)
    for name in _candidate_names(Path(source).stem):
        candidate = output_dir / name
        if not candidate.exists():
            return candidate


def _make_new_folder(output_dir: Path, names) -> Path:
    """Create and return the first folder that doesn't already exist.

    ``mkdir`` without ``exist_ok`` fails on anything already at the path
    (including dangling symlinks), so those names are skipped, never reused.
    """
    for name in names:
        path = output_dir / name
        try:
            path.mkdir(parents=True)
        except FileExistsError:
            continue
        return path


def process_pdf_to_jpgs(source, output_dir=None, password: str = "") -> Path:
    """Decrypt ``source`` and save one JPG per page into a Desktop folder.

    Returns the path to the created folder. Raises
    :class:`~pdfflatten.decrypt.PasswordRequired` if a password is needed but not
    supplied.
    """
    source = Path(source)
    output_dir = Path(output_dir) if output_dir is not None else desktop_dir()
    decrypted = decrypt_to_bytes(source, password=password)
    jpgs = pdf_to_jpegs(decrypted)
    folder = _make_new_folder(output_dir, _candidate_names(source.stem))
    pad = len(str(len(jpgs)))
    for index, data in enumerate(jpgs, start=1):
        (folder / f"{source.stem}-page-{index:0{pad}d}.jpg").write_bytes(data)
    return folder

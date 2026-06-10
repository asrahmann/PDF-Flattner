"""Orchestrate decrypt → flatten → save to a non-colliding Desktop path."""

from pathlib import Path

from .decrypt import decrypt_to_bytes
from .desktop import desktop_dir
from .flatten import flatten_pdf_bytes
from .images import pdf_to_jpegs


def output_path_for(source, output_dir) -> Path:
    """Compute ``flattened-<stem>.pdf`` in output_dir, avoiding overwrite with -2, -3…"""
    source = Path(source)
    output_dir = Path(output_dir)
    stem = source.stem
    candidate = output_dir / f"flattened-{stem}.pdf"
    counter = 2
    while candidate.exists():
        candidate = output_dir / f"flattened-{stem}-{counter}.pdf"
        counter += 1
    return candidate


def process_pdf(source, output_dir=None, password: str = "") -> Path:
    """Decrypt and flatten ``source``, write the result, and return its path.

    Raises :class:`~pdfflatten.decrypt.PasswordRequired` if the file needs an
    open password not supplied here.
    """
    source = Path(source)
    output_dir = Path(output_dir) if output_dir is not None else desktop_dir()
    decrypted = decrypt_to_bytes(source, password=password)
    flat = flatten_pdf_bytes(decrypted)
    out_path = output_path_for(source, output_dir)
    out_path.write_bytes(flat)
    return out_path


def output_folder_for(source, output_dir) -> Path:
    """Compute a folder named after the source stem, avoiding collisions with -2, -3…"""
    source = Path(source)
    output_dir = Path(output_dir)
    stem = source.stem
    candidate = output_dir / stem
    counter = 2
    while candidate.exists():
        candidate = output_dir / f"{stem}-{counter}"
        counter += 1
    return candidate


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
    folder = output_folder_for(source, output_dir)
    folder.mkdir(parents=True)
    pad = len(str(len(jpgs)))
    for index, data in enumerate(jpgs, start=1):
        (folder / f"{source.stem}-page-{index:0{pad}d}.jpg").write_bytes(data)
    return folder

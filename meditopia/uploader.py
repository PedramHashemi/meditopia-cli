"""
Walks a local directory and returns file tuples ready for upload.
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path


def collect_files(local_path: str) -> list[tuple[str, bytes, str]]:
    """
    Walk *local_path* (file or directory) and return a list of
    (relative_filename, file_bytes, mime_type) tuples.
    """
    root = Path(local_path).resolve()
    tuples: list[tuple[str, bytes, str]] = []

    if root.is_file():
        mime = mimetypes.guess_type(root.name)[0] or "application/octet-stream"
        tuples.append((root.name, root.read_bytes(), mime))
        return tuples

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            abs_path = Path(dirpath) / fname
            rel_path = str(abs_path.relative_to(root))
            mime = mimetypes.guess_type(fname)[0] or "application/octet-stream"
            tuples.append((rel_path, abs_path.read_bytes(), mime))

    return tuples

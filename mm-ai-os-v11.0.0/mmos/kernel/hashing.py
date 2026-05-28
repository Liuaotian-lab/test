from __future__ import annotations
from pathlib import Path
import hashlib
from typing import Iterable


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def hash_paths(paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(Path(x) for x in paths if Path(x).exists()):
        h.update(str(p).encode('utf-8'))
        if p.is_file():
            h.update(sha256_file(p).encode('utf-8'))
    return h.hexdigest()

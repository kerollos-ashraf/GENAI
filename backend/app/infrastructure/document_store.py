"""Filesystem storage for knowledge-base documents (the `data/policies` folder)."""

import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from app.domain.errors import NotFoundError


@dataclass(frozen=True)
class StoredFile:
    name: str
    size_bytes: int
    path: Path


class FileSystemDocumentStore:
    """Lists, reads and atomically writes documents in one folder. Hidden files (including
    in-progress uploads) and unsupported extensions are ignored."""

    def __init__(self, root: Path, extensions: Iterable[str]) -> None:
        self._root = Path(root)
        self._extensions = {e.lower() for e in extensions}
        self._root.mkdir(parents=True, exist_ok=True)

    def files(self) -> list[StoredFile]:
        return [
            StoredFile(p.name, p.stat().st_size, p)
            for p in sorted(self._root.iterdir())
            if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in self._extensions
        ]

    def signature(self) -> tuple:
        """Cheap change detector: names, sizes and modification times."""
        return tuple((f.name, f.path.stat().st_mtime_ns, f.size_bytes) for f in self.files())

    def read(self, name: str) -> bytes:
        return self._path(name).read_bytes()

    def write(self, name: str, data: bytes) -> None:
        fd, tmp = tempfile.mkstemp(dir=self._root, prefix=".upload-")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, self._root / name)

    def delete(self, name: str) -> None:
        self._path(name).unlink()

    def _path(self, name: str) -> Path:
        path = self._root / name
        if not path.is_file():
            raise NotFoundError(f"{name} not found")
        return path

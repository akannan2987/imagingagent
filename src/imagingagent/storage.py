"""The storage abstraction: where bytes live.

Every layer of the pipeline reads and writes through this interface and
never touches the disk directly. Today there is one backend, ``LocalStorage``
(a folder on your machine). Later, an object-storage backend (S3-compatible
buckets) can be added by writing one more class here — the ingestion, audit
and report code will not change by a single line. That is the point of an
abstraction: one contract, many implementations.

Keys are always written with forward slashes (``runs/abc/report.json``),
whatever the operating system. ``LocalStorage`` converts them to real paths
with ``pathlib``, which knows about Windows backslashes so we do not have to.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath
from typing import Any

from .config import StorageConfig


class StorageError(Exception):
    """Raised for invalid keys or backend failures."""


class Storage(ABC):
    """The contract. Subclasses implement the six abstract methods; the
    convenience helpers (text/json) are shared."""

    # ---- abstract: every backend must provide these -------------------------

    @abstractmethod
    def write_bytes(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def read_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]: ...

    @abstractmethod
    def local_path(self, key: str) -> Path:
        """A real filesystem path for the key.

        Libraries that read images (nibabel, SimpleITK) want a path, not
        bytes. Local storage returns the path directly; a remote backend
        would download to a cache and return that path.
        """

    # ---- shared helpers -----------------------------------------------------

    def write_text(self, key: str, text: str) -> None:
        self.write_bytes(key, text.encode("utf-8"))

    def read_text(self, key: str) -> str:
        return self.read_bytes(key).decode("utf-8")

    def write_json(self, key: str, obj: Any) -> None:
        # indent=2 keeps files human-readable; sort_keys keeps diffs stable.
        self.write_text(key, json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")

    def read_json(self, key: str) -> Any:
        return json.loads(self.read_text(key))

    def append_text(self, key: str, text: str) -> None:
        """Append to a text file (used by the run ledger). Default: read + write."""
        existing = self.read_text(key) if self.exists(key) else ""
        self.write_text(key, existing + text)


def validate_key(key: str) -> PurePosixPath:
    """Reject keys that could escape the storage root.

    ``../secrets.txt`` or an absolute path must never be accepted: the
    storage root is a boundary, and a boundary with holes is not one.
    """
    if not key or key.strip() != key:
        raise StorageError(f"Invalid storage key: {key!r}")
    posix = PurePosixPath(key)
    if posix.is_absolute() or "\\" in key:
        raise StorageError(f"Storage keys must be relative, forward-slash paths: {key!r}")
    if any(part in ("..", "") for part in posix.parts):
        raise StorageError(f"Storage keys may not contain '..': {key!r}")
    return posix


class LocalStorage(Storage):
    """Files in a folder. The default and, for a single machine, all you need."""

    def __init__(self, base_dir: Path | str = ".") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        posix = validate_key(key)
        return self.base_dir.joinpath(*posix.parts)

    def write_bytes(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read_bytes(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise StorageError(f"Key not found: {key}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def list_keys(self, prefix: str = "") -> list[str]:
        """All keys under a prefix, sorted, always with forward slashes."""
        root = self._path(prefix) if prefix else self.base_dir
        if not root.exists():
            return []
        files = (p for p in root.rglob("*") if p.is_file())
        return sorted(p.relative_to(self.base_dir).as_posix() for p in files)

    def local_path(self, key: str) -> Path:
        return self._path(key)

    def append_text(self, key: str, text: str) -> None:
        # Local disk can append in place — cheaper than read + rewrite.
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)


def get_storage(config: StorageConfig) -> Storage:
    """Build the backend named in the configuration."""
    if config.backend == "local":
        return LocalStorage(config.base_dir)
    raise StorageError(f"Unknown storage backend: {config.backend}")  # pragma: no cover

"""Small helpers shared by every layer: hashing, timestamps, identifiers.

Kept in one place so the same definition of "now" and the same hash
function are used everywhere — a run ledger is only useful if every entry
was stamped the same way.
"""

from __future__ import annotations

import hashlib
import platform
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path


def utc_now_iso() -> str:
    """Current time in UTC as an ISO-8601 string, e.g. ``2026-09-01T14:03:22Z``.

    UTC (not local time) so that runs made in Basel and San Francisco sort
    correctly in the same ledger.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def short_id() -> str:
    """A 12-character random identifier — enough to be unique in one project."""
    return uuid.uuid4().hex[:12]


def sha256_bytes(data: bytes) -> str:
    """Fingerprint of a byte string. Same bytes → same fingerprint, always."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Fingerprint of a file, read in 1 MB chunks so huge volumes fit in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def platform_summary() -> str:
    """One line describing the machine, e.g. ``Windows-11 / CPython 3.11.9``."""
    return (
        f"{platform.system()}-{platform.release()} / "
        f"{platform.python_implementation()} {sys.version.split()[0]}"
    )

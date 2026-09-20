"""Shared helpers for the dataset download scripts: resumable download,
checksums recorded on first run and verified on later runs, zip/tar
extraction. Every ``download_<name>.py`` imports from here so the behaviour
— and the provenance record it leaves — is identical for every dataset.
"""

from __future__ import annotations

import hashlib
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def hashes(path: Path) -> dict[str, str]:
    """SHA-256, MD5 and size of a file, read in 1 MB chunks."""
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            sha.update(chunk)
            md5.update(chunk)
    return {"sha256": sha.hexdigest(), "md5": md5.hexdigest(), "bytes": str(path.stat().st_size)}


def download(url: str, dest: Path, headers: dict[str, str] | None = None) -> Path:
    """Download ``url`` to ``dest``, resuming a partial file if one exists."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.stat().st_size if dest.exists() else 0
    request_headers = {
        "User-Agent": "imagingagent/0.1 (dataset download script)",
        **(headers or {}),
    }
    if existing:
        request_headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request) as response:
        if existing and response.status == 200:  # server ignored the Range header: start over
            existing = 0
        total = existing + int(response.headers.get("Content-Length", 0) or 0)
        done = existing
        with dest.open("ab" if existing else "wb") as fh:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done / 1e6:8.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()
    return dest


def record_or_verify(
    archive: Path, checksums: Path, url: str, expected_md5: str | None = None
) -> dict[str, str]:
    """First run: write CHECKSUMS.txt. Later runs: verify against it. Optional publisher MD5."""
    current = hashes(archive)
    if expected_md5 and current["md5"] != expected_md5:
        raise SystemExit(
            f"MD5 mismatch for {archive.name}: got {current['md5']}, publisher says {expected_md5}. Delete the file and retry."
        )
    if checksums.exists():
        recorded = dict(
            line.split("=", 1)
            for line in checksums.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        for key, value in current.items():
            if recorded.get(key) != value:
                raise SystemExit(
                    f"CHECKSUM MISMATCH ({key}) for {archive.name}: the download changed since it was recorded."
                )
        print(f"checksums verified against {checksums}")
    else:
        checksums.parent.mkdir(parents=True, exist_ok=True)
        checksums.write_text(
            "".join(f"{k}={v}\n" for k, v in current.items()) + f"url={url}\nfile={archive.name}\n",
            encoding="utf-8",
        )
        print(f"checksums recorded in {checksums}")
    return current


def extract(archive: Path, target: Path) -> None:
    """Extract a .zip or .tar into ``target``, skipping macOS ``._`` artefacts."""
    target.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            members = [
                m
                for m in zf.namelist()
                if not Path(m).name.startswith("._") and "__MACOSX" not in m
            ]
            zf.extractall(target, members=members)
    else:
        with tarfile.open(archive) as tar:
            members = [m for m in tar.getmembers() if not Path(m.name).name.startswith("._")]
            tar.extractall(target, members=members, filter="data")


def already_present(marker: Path, description: str) -> bool:
    if marker.exists():
        print(f"already present: {description} ({marker})")
        return True
    return False

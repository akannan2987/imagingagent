"""Download Medical Segmentation Decathlon Task 04 (Hippocampus) into data/raw/.

Run from the repository root, with the virtual environment active:

    python scripts/download_msd_hippocampus.py            # download + extract + record checksums
    python scripts/download_msd_hippocampus.py --verify   # re-check an existing download

What it does, and why each step exists:
  1. Downloads the archive (about 0.4 GB) from the public mirror hosted for
     the MONAI project on AWS, resuming if a partial file exists.
  2. Computes SHA-256 and MD5 of the archive. On the first run it *records*
     them in data/raw/msd_task04/CHECKSUMS.txt; on later runs it *verifies*
     against that file. That is provenance: proof the data never changed.
  3. Extracts into data/raw/msd_task04/ (imagesTr/, labelsTr/, imagesTs/,
     dataset.json) and never touches the files again.

Licence: CC-BY-SA 4.0 (Antonelli et al., Nature Communications 2022).
No account is needed. Nothing here contains personal data.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tarfile
import urllib.request
from pathlib import Path

URL = "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task04_Hippocampus.tar"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ARCHIVE = RAW / "Task04_Hippocampus.tar"
TARGET = RAW / "msd_task04"
CHECKSUMS = TARGET / "CHECKSUMS.txt"


def hashes(path: Path) -> dict[str, str]:
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            sha.update(chunk)
            md5.update(chunk)
    return {"sha256": sha.hexdigest(), "md5": md5.hexdigest(), "bytes": str(path.stat().st_size)}


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.stat().st_size if dest.exists() else 0
    request = urllib.request.Request(
        url, headers={"Range": f"bytes={existing}-"} if existing else {}
    )
    with urllib.request.urlopen(request) as response:
        total = existing + int(response.headers.get("Content-Length", 0))
        mode = "ab" if existing else "wb"
        done = existing
        with dest.open(mode) as fh:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done / 1e6:8.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()


def extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if not Path(m.name).name.startswith("._")]
        # The archive has one top folder (Task04_Hippocampus/); strip it.
        for m in members:
            parts = Path(m.name).parts
            m.name = str(Path(*parts[1:])) if len(parts) > 1 else ""
        members = [m for m in members if m.name]
        tar.extractall(target, members=members, filter="data")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--verify", action="store_true", help="only verify checksums of an existing download"
    )
    parser.add_argument(
        "--keep-archive", action="store_true", help="keep the .tar after extraction"
    )
    args = parser.parse_args(argv)

    if args.verify:
        if not CHECKSUMS.exists() or not ARCHIVE.exists():
            print(
                "nothing to verify: run without --verify first (the archive is deleted after extraction unless --keep-archive)"
            )
            return 1
        recorded = dict(
            line.split("=", 1) for line in CHECKSUMS.read_text().splitlines() if "=" in line
        )
        current = hashes(ARCHIVE)
        ok = all(recorded.get(k) == v for k, v in current.items())
        print("checksums match" if ok else "CHECKSUM MISMATCH — the archive changed")
        return 0 if ok else 1

    if (TARGET / "imagesTr").is_dir() and any((TARGET / "imagesTr").glob("*.nii.gz")):
        print(f"already extracted: {TARGET}")
        return 0

    print(f"downloading {URL}")
    download(URL, ARCHIVE)
    h = hashes(ARCHIVE)
    print(f"sha256 {h['sha256']}\nmd5    {h['md5']}\nbytes  {h['bytes']}")
    print(f"extracting to {TARGET}")
    extract(ARCHIVE, TARGET)
    CHECKSUMS.write_text(
        "".join(f"{k}={v}\n" for k, v in h.items()) + f"url={URL}\n", encoding="utf-8"
    )
    n = len(list((TARGET / "imagesTr").glob("*.nii.gz")))
    print(f"done: {n} training volumes in {TARGET / 'imagesTr'}; checksums recorded in {CHECKSUMS}")
    if not args.keep_archive:
        ARCHIVE.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())

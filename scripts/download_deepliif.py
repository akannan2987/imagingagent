"""Download a DeepLIIF image set: co-registered IHC and multiplex IF (CC-BY 4.0).

    python scripts/download_deepliif.py                    # validation set, 161 MB (default)
    python scripts/download_deepliif.py --split testing    # 1.0 GB

Each case is one wide PNG: IHC | Hematoxylin | DAPI | Lap2 | Marker | Seg,
six 512×512 panels side by side (Ghahremani et al., Nature Machine
Intelligence 2022; Zenodo record 4751737). The publisher's MD5 for each
archive is checked before extraction. Lands in data/raw/deepliif/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _download import RAW, already_present, download, extract, record_or_verify  # noqa: E402

FILES = {
    "validation": ("DeepLIIF_Validation_Set.zip", "3387c41b2d6771968976a1a6e67202dc"),
    "testing": ("DeepLIIF_Testing_Set.zip", "665899936c8012754524258ed16667ea"),
    "training": ("DeepLIIF_Training_Set.zip", "f4812639cbee1f6732cb206e1e6acdc8"),
}
BASE = "https://zenodo.org/records/4751737/files/"
TARGET = RAW / "deepliif"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--split", default="validation", choices=sorted(FILES))
    args = parser.parse_args(argv)
    filename, md5 = FILES[args.split]
    folder = TARGET / filename.replace(".zip", "")
    if already_present(folder, f"DeepLIIF {args.split} set"):
        return 0
    url = f"{BASE}{filename}?download=1"
    archive = TARGET / filename
    print(f"downloading {url}")
    download(url, archive)
    record_or_verify(archive, TARGET / f"CHECKSUMS_{args.split}.txt", url, expected_md5=md5)
    extract(archive, TARGET)
    archive.unlink()
    n = sum(1 for _ in TARGET.rglob("*.png"))
    print(f"done: {n} composite images under {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

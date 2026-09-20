"""Download the Kather 2016 colorectal-cancer texture tiles (CC-BY 4.0).

    python scripts/download_kather2016.py

5,000 H&E tiles of 150×150 px at 0.495 µm/px in eight tissue-class folders,
from Zenodo record 53169 (Kather et al., Scientific Reports 2016). Lands in
data/raw/kather2016/Kather_texture_2016_image_tiles_5000/<NN_CLASS>/*.tif
with checksums recorded beside it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _download import RAW, already_present, download, extract, record_or_verify  # noqa: E402

URL = "https://zenodo.org/record/53169/files/Kather_texture_2016_image_tiles_5000.zip"
TARGET = RAW / "kather2016"
ARCHIVE = TARGET / "Kather_texture_2016_image_tiles_5000.zip"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--keep-archive", action="store_true", help="keep the downloaded archive after extraction"
    )
    args = parser.parse_args(argv)
    if already_present(
        TARGET / "Kather_texture_2016_image_tiles_5000" / "01_TUMOR", "Kather-2016 tiles"
    ):
        return 0
    print(f"downloading {URL}")
    download(URL, ARCHIVE)
    record_or_verify(ARCHIVE, TARGET / "CHECKSUMS.txt", URL)
    extract(ARCHIVE, TARGET)
    if not args.keep_archive:
        ARCHIVE.unlink()
    n = sum(1 for _ in (TARGET / "Kather_texture_2016_image_tiles_5000").rglob("*.tif"))
    print(f"done: {n} tiles under {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

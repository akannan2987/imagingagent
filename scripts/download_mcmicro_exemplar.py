"""Download MCMICRO exemplar-001: a small multiplex-immunofluorescence (CyCIF) core.

    python scripts/download_mcmicro_exemplar.py

240 MB zip (320 MB unzipped) from the MCMICRO project (Schapiro et al.,
Nature Methods 2022): a lung adenocarcinoma TMA core imaged in three
cycles, six four-channel tiles per cycle, twelve channels in total, as
raw OME-TIFF plus markers.csv naming the channels. The tiles are
unstitched and unregistered — registering the cycles to each other is a
Phase 2 task. Lands in data/raw/mcmicro_exemplar001/exemplar-001/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _download import RAW, already_present, download, extract, record_or_verify  # noqa: E402

URL = "https://mcmicro.s3.amazonaws.com/exemplars/exemplar-001.zip"
TARGET = RAW / "mcmicro_exemplar001"
ARCHIVE = TARGET / "exemplar-001.zip"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--keep-archive", action="store_true", help="keep the downloaded archive after extraction"
    )
    args = parser.parse_args(argv)
    if already_present(TARGET / "exemplar-001" / "markers.csv", "MCMICRO exemplar-001"):
        return 0
    print(f"downloading {URL}")
    download(URL, ARCHIVE)
    record_or_verify(ARCHIVE, TARGET / "CHECKSUMS.txt", URL)
    extract(ARCHIVE, TARGET)
    if not args.keep_archive:
        ARCHIVE.unlink()
    n = sum(1 for _ in TARGET.rglob("*.ome.tif*"))
    print(f"done: {n} OME-TIFF cycle files under {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

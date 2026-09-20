"""Download the 10x Visium mouse-brain sample used by the squidpy project.

    python scripts/download_visium_sample.py

The file is an AnnData (.h5ad, ≈ 0.4–0.5 GB) with the spot-by-gene matrix,
spot coordinates and the hires H&E image. Two routes, tried in order:

  1. the direct download the squidpy project hosts (no extra library);
  2. if that fails, ``squidpy.datasets.visium_hne_adata`` — requires
     ``python -m pip install squidpy`` (a Phase 7 dependency), and the
     script says so instead of guessing.

Lands in data/raw/visium_hne/visium_hne_adata.h5ad with checksums recorded.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _download import RAW, already_present, download, record_or_verify  # noqa: E402

DIRECT_URL = "https://ndownloader.figshare.com/files/26098397"
TARGET = RAW / "visium_hne"
FILE = TARGET / "visium_hne_adata.h5ad"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.parse_args(argv)
    if already_present(FILE, "Visium H&E sample"):
        return 0
    try:
        print(f"downloading {DIRECT_URL}")
        download(DIRECT_URL, FILE)
        record_or_verify(FILE, TARGET / "CHECKSUMS.txt", DIRECT_URL)
    except Exception as exc:  # noqa: BLE001 - any download failure falls back to squidpy
        print(f"direct download failed ({exc}); trying squidpy ...")
        if FILE.exists():
            FILE.unlink()
        try:
            import squidpy as sq
        except ImportError:
            print(
                "squidpy is not installed. Either retry later, or: python -m pip install squidpy  (then rerun)"
            )
            return 1
        TARGET.mkdir(parents=True, exist_ok=True)
        sq.datasets.visium_hne_adata(path=str(FILE))
        record_or_verify(FILE, TARGET / "CHECKSUMS.txt", "squidpy.datasets.visium_hne_adata")
    # Sanity check that it opens as a Visium AnnData.
    from imagingagent.tracks.pathology.io import read_visium_h5ad

    adata, image, geometry = read_visium_h5ad(FILE)
    print(
        f"done: {adata.n_obs} spots × {adata.n_vars} genes; hires image {image.shape[1]}×{image.shape[0]} px ≈ {geometry.microns_per_pixel:.2f} µm/px"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

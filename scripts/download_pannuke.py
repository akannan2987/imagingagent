"""Download one PanNuke fold from the Hugging Face mirror and extract a subset.

    python scripts/download_pannuke.py                 # fold3, 500 tiles (config default)
    python scripts/download_pannuke.py --fold fold1 --tiles 300 --seed 7

PanNuke (Gamper et al. 2019/2020) is CC-BY-NC-SA 4.0 — non-commercial; every
result derived from it inherits that. The mirror (RationAI/PanNuke) stores
each fold as one Parquet file (≈ 280 MB); a seeded subset is extracted to
data/raw/pannuke/extracted/<fold>/ as PNG tiles + .npz labels + index.csv
so later phases never decode the whole fold again. The Parquet file is kept
as the raw download with its checksum recorded.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _download import RAW, download, record_or_verify  # noqa: E402

BASE = "https://huggingface.co/datasets/RationAI/PanNuke/resolve/main/data/"
TARGET = RAW / "pannuke"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fold", default="fold3", choices=["fold1", "fold2", "fold3"])
    parser.add_argument(
        "--tiles",
        type=int,
        default=None,
        help="how many tiles to extract (default: config tracks.pathology.pannuke_tiles)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="subset seed (default: config tracks.pathology.seed)"
    )
    args = parser.parse_args(argv)

    from imagingagent.config import load_config
    from imagingagent.tracks.pathology.pannuke import extract_subset

    cfg = load_config(
        Path("configs/default.yaml") if Path("configs/default.yaml").exists() else None
    )
    n_tiles = args.tiles or cfg.tracks.pathology.pannuke_tiles
    seed = args.seed if args.seed is not None else cfg.tracks.pathology.seed

    filename = f"{args.fold}-00000-of-00001.parquet"
    url = BASE + filename
    parquet = TARGET / filename
    if not parquet.exists():
        print(f"downloading {url}")
        download(url, parquet)
    record_or_verify(parquet, TARGET / f"CHECKSUMS_{args.fold}.txt", url)
    print(f"extracting {n_tiles} tiles (seed {seed}) from {parquet.name} ...")
    rows = extract_subset(parquet, TARGET / "extracted", n_tiles, seed, fold=args.fold)
    print(
        f"done: {len(rows)} tiles under {TARGET / 'extracted' / args.fold}; licence CC-BY-NC-SA 4.0 (non-commercial)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

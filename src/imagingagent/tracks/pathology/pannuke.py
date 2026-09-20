"""PanNuke: extracting per-tile files from the Parquet mirror.

The Hugging Face mirror stores each fold as one Parquet table with four
columns: ``image`` (a PNG), ``instances`` (a list of binary PNG masks, one
per nucleus), ``categories`` (one class per nucleus) and ``tissue`` (one
tissue type per tile). Working straight from Parquet in every phase would
mean decoding hundreds of megabytes each run, so the download script
extracts a seeded subset into plain files once:

    extracted/<fold>/images/<case_id>.png       the RGB tile
    extracted/<fold>/labels/<case_id>.npz       instances (uint16 map), types (int8)
    extracted/<fold>/index.csv                  case_id, row, tissue, n_nuclei

The Parquet file stays as the raw download; the extracted files are derived
from it and can be regenerated with the same seed.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .io import decode_png_bytes, write_rgb_png

NUCLEUS_TYPES = ("Neoplastic", "Inflammatory", "Connective", "Dead", "Epithelial")
TISSUE_TYPES = (
    "Adrenal Gland",
    "Bile Duct",
    "Bladder",
    "Breast",
    "Cervix",
    "Colon",
    "Esophagus",
    "Head & Neck",
    "Kidney",
    "Liver",
    "Lung",
    "Ovarian",
    "Pancreatic",
    "Prostate",
    "Skin",
    "Stomach",
    "Testis",
    "Thyroid",
    "Uterus",
)


def _png_bytes(cell) -> bytes:
    """The HF image feature is a struct {bytes, path}; some writers store raw bytes."""
    if isinstance(cell, dict):
        return cell["bytes"]
    return cell


def row_to_tile(row: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """One Parquet row → (image H×W×3, instance map H×W uint16, types int8, tissue int)."""
    image = decode_png_bytes(_png_bytes(row["image"]))
    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    image = image[..., :3].astype(np.uint8)
    instances = np.zeros(image.shape[:2], dtype=np.uint16)
    for k, mask_cell in enumerate(row["instances"] or [], start=1):
        mask = decode_png_bytes(_png_bytes(mask_cell))
        instances[(mask > 0) & (instances == 0)] = k
    types = np.asarray(row["categories"] or [], dtype=np.int8)
    return image, instances, types, int(row["tissue"])


def extract_subset(
    parquet_path: Path, out_dir: Path, n_tiles: int, seed: int, fold: str = "fold3"
) -> list[dict]:
    """Extract a seeded subset of tiles from one fold's Parquet file. Returns the index rows."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "pyarrow is required: python -m pip install -r requirements-pathology.txt"
        ) from exc

    table = pq.read_table(str(parquet_path))
    total = table.num_rows
    rng = np.random.default_rng(seed)
    chosen = np.sort(rng.choice(total, size=min(n_tiles, total), replace=False))
    out_dir = Path(out_dir) / fold
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for r in chosen:
        row = table.slice(int(r), 1).to_pylist()[0]
        image, instances, types, tissue = row_to_tile(row)
        case_id = f"pannuke_{fold}_{int(r):05d}"
        write_rgb_png(image, out_dir / "images" / f"{case_id}.png")
        np.savez_compressed(out_dir / "labels" / f"{case_id}.npz", instances=instances, types=types)
        rows.append(
            {
                "case_id": case_id,
                "row": int(r),
                "tissue": TISSUE_TYPES[tissue] if tissue < len(TISSUE_TYPES) else str(tissue),
                "n_nuclei": int(instances.max()),
            }
        )
    with (out_dir / "index.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "row", "tissue", "n_nuclei"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def read_index(out_dir: Path, fold: str = "fold3") -> list[dict]:
    path = Path(out_dir) / fold / "index.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

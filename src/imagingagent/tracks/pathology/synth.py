"""Synthetic slides: stand-ins for the five pathology datasets.

Three generators, all seeded, all labelled synthetic in every output:

- **H&E-like tiles** with drawn nuclei: an RGB tile with a pinkish
  "cytoplasm" background, dark-purple elliptical nuclei of several sizes,
  a tissue-class label (eight classes, as Kather-2016) drawn by texture,
  plus the exact instance map and per-nucleus type (as PanNuke). One
  generator serves both the *tissue* and the *nuclei* roles.
- **Multi-channel fluorescence tiles**: a DAPI channel lighting every
  nucleus and marker channels lighting subsets of them, written as
  OME-TIFF with channel names (as MCMICRO) — and, side by side with a
  DAB-brown rendering of the same cells, as a DeepLIIF-style composite.
- **Spot matrices**: a grid of spots over a synthetic H&E image with a few
  "genes" whose counts follow drawn regions, saved as ``.h5ad`` (as Visium).

Crash-test dummies, not patients. They exist so every command runs
offline and every test runs in seconds.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ...schemas import TileGeometry
from .io import write_ome_tiff, write_rgb_png

TISSUE_CLASSES = ("TUMOR", "STROMA", "COMPLEX", "LYMPHO", "DEBRIS", "MUCOSA", "ADIPOSE", "EMPTY")
NUCLEUS_TYPES = ("Neoplastic", "Inflammatory", "Connective", "Dead", "Epithelial")


@dataclass(frozen=True)
class SyntheticTileSpec:
    size: int = 256
    microns_per_pixel: float = 0.25
    nuclei_range: tuple[int, int] = (20, 90)
    radius_range_px: tuple[float, float] = (5.0, 11.0)


def _ellipse_mask(
    size: int, cx: float, cy: float, rx: float, ry: float, angle: float
) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    x = (xx - cx) * np.cos(angle) + (yy - cy) * np.sin(angle)
    y = -(xx - cx) * np.sin(angle) + (yy - cy) * np.cos(angle)
    return (x / rx) ** 2 + (y / ry) ** 2 <= 1.0


def make_he_tile(
    rng: np.random.Generator, spec: SyntheticTileSpec, tissue_class: int | None = None
) -> dict:
    """One H&E-like tile with instance map, nucleus types and a tissue class."""
    size = spec.size
    tissue_class = int(rng.integers(len(TISSUE_CLASSES))) if tissue_class is None else tissue_class
    # Background: class-dependent tint and texture so tissue classes are separable.
    base = np.array(
        [
            [238, 205, 222],
            [236, 196, 214],
            [228, 186, 204],
            [230, 210, 230],
            [214, 192, 196],
            [240, 215, 228],
            [246, 240, 244],
            [250, 250, 250],
        ][tissue_class],
        dtype=float,
    )
    texture = rng.normal(0, 6 + 2 * tissue_class, size=(size, size, 1))
    stripes = 8 * np.sin(np.linspace(0, (tissue_class + 1) * 3.0, size))[None, :, None]
    image = np.clip(base[None, None, :] + texture + stripes, 0, 255)

    n_nuclei = (
        int(rng.integers(*spec.nuclei_range)) if tissue_class != 7 else int(rng.integers(0, 4))
    )
    instances = np.zeros((size, size), dtype=np.uint16)
    types: list[int] = []
    for k in range(1, n_nuclei + 1):
        cx, cy = rng.uniform(4, size - 4, size=2)
        rx = rng.uniform(*spec.radius_range_px)
        ry = rx * rng.uniform(0.6, 1.0)
        mask = _ellipse_mask(size, cx, cy, rx, ry, rng.uniform(0, np.pi)) & (instances == 0)
        if mask.sum() < 12:
            continue
        instances[mask] = k
        nucleus_type = int(rng.choice(len(NUCLEUS_TYPES), p=[0.45, 0.25, 0.18, 0.04, 0.08]))
        types.append(nucleus_type)
        colour = np.array(
            [[70, 40, 110], [40, 30, 90], [95, 60, 120], [30, 20, 40], [80, 50, 105]][nucleus_type],
            dtype=float,
        )
        image[mask] = colour + rng.normal(0, 8, size=3)
    # Renumber instances densely (some ellipses were rejected).
    unique = np.unique(instances[instances > 0])
    remap = {old: new for new, old in enumerate(unique, start=1)}
    dense = np.zeros_like(instances)
    for old, new in remap.items():
        dense[instances == old] = new
    image = np.clip(image + rng.normal(0, 3, size=image.shape), 0, 255).astype(np.uint8)
    geometry = TileGeometry(
        microns_per_pixel=spec.microns_per_pixel,
        width=size,
        height=size,
        magnification=40.0,
        channels=["R", "G", "B"],
        stain="HE",
    )
    return {
        "image": image,
        "instances": dense,
        "types": np.asarray(types, dtype=np.int8),
        "tissue_class": tissue_class,
        "geometry": geometry,
    }


def make_mif_tile(
    rng: np.random.Generator,
    instances: np.ndarray,
    markers: tuple[str, ...] = ("DAPI", "CD8", "PanCK", "Ki67"),
) -> tuple[np.ndarray, np.ndarray]:
    """Fluorescence channels for an existing instance map → (C×H×W uint16, positivity per nucleus × marker)."""
    n = int(instances.max())
    channels = np.zeros((len(markers), *instances.shape), dtype=np.float64)
    positivity = np.zeros((n, len(markers)), dtype=bool)
    for k in range(1, n + 1):
        mask = instances == k
        channels[0][mask] = rng.uniform(0.6, 1.0)  # DAPI: every nucleus
        positivity[k - 1, 0] = True
        for c in range(1, len(markers)):
            if rng.random() < (0.25, 0.4, 0.3)[(c - 1) % 3]:
                channels[c][mask] = rng.uniform(0.5, 1.0)
                positivity[k - 1, c] = True
    channels += rng.normal(0.02, 0.01, size=channels.shape).clip(0)
    channels = (channels.clip(0, 1) * 4000).astype(np.uint16)
    return channels, positivity


def render_dab(image_he: np.ndarray, instances: np.ndarray, positive: np.ndarray) -> np.ndarray:
    """IHC-like rendering: positive nuclei brown (DAB), the rest light blue (hematoxylin)."""
    out = np.full_like(image_he, 235)
    out[..., 0] = 225
    out[..., 1] = 232
    for k in range(1, int(instances.max()) + 1):
        mask = instances == k
        out[mask] = (120, 70, 30) if positive[k - 1] else (140, 150, 200)
    return out


def _grey(channels: np.ndarray, index: int) -> np.ndarray:
    """One fluorescence channel rendered as an 8-bit grey RGB panel."""
    return np.repeat((channels[index] / 4000 * 255).astype(np.uint8)[..., None], 3, axis=-1)


def generate_synthetic_he(
    out_dir: Path, n_tiles: int, seed: int, spec: SyntheticTileSpec | None = None
) -> list[dict]:
    """Write H&E tiles (+ instance labels + tissue classes). Returns per-tile records."""
    spec = spec or SyntheticTileSpec()
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir)
    records = []
    for i in range(n_tiles):
        tile = make_he_tile(rng, spec, tissue_class=i % len(TISSUE_CLASSES))
        case_id = f"synthetic_he_{i:03d}"
        image_path = write_rgb_png(tile["image"], out_dir / "images" / f"{case_id}.png")
        label_path = out_dir / "labels" / f"{case_id}.npz"
        label_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            label_path,
            instances=tile["instances"],
            types=tile["types"],
            tissue_class=np.int8(tile["tissue_class"]),
        )
        records.append(
            {
                "case_id": case_id,
                "image_path": image_path,
                "label_path": label_path,
                "geometry": tile["geometry"],
                "tissue_class": TISSUE_CLASSES[tile["tissue_class"]],
            }
        )
    return records


def generate_synthetic_mif(
    out_dir: Path, n_tiles: int, seed: int, spec: SyntheticTileSpec | None = None
) -> list[dict]:
    """Write multi-channel OME-TIFF tiles and matching IHC composites."""
    spec = spec or SyntheticTileSpec()
    rng = np.random.default_rng(seed + 1)
    out_dir = Path(out_dir)
    markers = ("DAPI", "CD8", "PanCK", "Ki67")
    records = []
    for i in range(n_tiles):
        tile = make_he_tile(rng, spec, tissue_class=0)
        channels, positivity = make_mif_tile(rng, tile["instances"], markers)
        geometry = TileGeometry(
            microns_per_pixel=spec.microns_per_pixel,
            width=spec.size,
            height=spec.size,
            magnification=40.0,
            channels=list(markers),
            stain="MIF",
        )
        case_id = f"synthetic_mif_{i:03d}"
        ome_path = write_ome_tiff(channels, geometry, out_dir / "ome" / f"{case_id}.ome.tif")
        # DeepLIIF-style composite: IHC (Ki67 as DAB) | Hematoxylin | DAPI | Lap2 | Marker | Seg
        ihc = render_dab(tile["image"], tile["instances"], positivity[:, 3])
        seg = np.repeat(((tile["instances"] > 0) * 255).astype(np.uint8)[..., None], 3, axis=-1)
        composite = np.concatenate(
            [
                ihc,
                _grey(channels, 0),
                _grey(channels, 0),
                _grey(channels, 1),
                _grey(channels, 3),
                seg,
            ],
            axis=1,
        )
        composite_path = write_rgb_png(composite, out_dir / "ihc_composite" / f"{case_id}.png")
        label_path = out_dir / "labels" / f"{case_id}.npz"
        label_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            label_path,
            instances=tile["instances"],
            positivity=positivity,
            markers=np.array(markers),
        )
        records.append(
            {
                "case_id": case_id,
                "ome_path": ome_path,
                "composite_path": composite_path,
                "label_path": label_path,
                "geometry": geometry,
            }
        )
    return records


def generate_synthetic_spots(
    out_dir: Path, seed: int, n_side: int = 24, spec: SyntheticTileSpec | None = None
) -> dict:
    """Write one Visium-like AnnData: a spot grid over a synthetic H&E image with 6 'genes'."""
    try:
        import anndata
        import pandas as pd
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "anndata is required: python -m pip install -r requirements-pathology.txt"
        ) from exc
    spec = spec or SyntheticTileSpec(size=600, microns_per_pixel=0.5)
    rng = np.random.default_rng(seed + 2)
    tile = make_he_tile(
        rng,
        SyntheticTileSpec(
            size=spec.size, microns_per_pixel=spec.microns_per_pixel, nuclei_range=(300, 500)
        ),
        tissue_class=0,
    )
    image = tile["image"]
    size = spec.size
    # Spot grid in full-resolution pixels; 100 µm centre-to-centre → 200 px at 0.5 µm/px, scaled to fit.
    step = size / (n_side + 1)
    coords = np.array(
        [(step * (i + 1), step * (j + 1)) for j in range(n_side) for i in range(n_side)]
    )
    # Two drawn regions drive gene expression: a left "tumour" half and a right "stroma" half.
    region = (coords[:, 0] > size / 2).astype(int)
    genes = ["GENE_T1", "GENE_T2", "GENE_S1", "GENE_S2", "GENE_HK1", "GENE_HK2"]
    means = np.array([[40, 30, 3, 2, 20, 15], [4, 3, 35, 28, 20, 15]])[region]
    counts = rng.poisson(means).astype(np.float32)
    adata = anndata.AnnData(
        X=counts,
        obs=pd.DataFrame(
            {"region": np.where(region == 0, "tumour", "stroma")},
            index=[f"spot_{k:04d}" for k in range(len(coords))],
        ),
        var=pd.DataFrame(index=genes),
    )
    adata.obsm["spatial"] = coords
    adata.uns["spatial"] = {
        "synthetic": {
            "images": {"hires": image},
            "scalefactors": {
                "tissue_hires_scalef": 1.0,
                "spot_diameter_fullres": 55.0 / spec.microns_per_pixel,
            },
        }
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "synthetic_visium.h5ad"
    adata.write_h5ad(path)
    return {
        "case_id": "synthetic_visium_000",
        "path": path,
        "n_spots": len(coords),
        "geometry": TileGeometry(
            microns_per_pixel=spec.microns_per_pixel,
            width=size,
            height=size,
            channels=["R", "G", "B"],
            stain="HE",
        ),
    }

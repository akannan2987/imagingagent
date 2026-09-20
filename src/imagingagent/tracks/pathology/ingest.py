"""Ingestion for the pathology track: five dataset roles, one manifest.

Each role in the configuration (tissue, nuclei, ihc, mif, spatial) maps to
one public dataset and one synthetic stand-in. For every enabled role the
real data is used when its folder exists; otherwise the synthetic generator
runs (if the config allows). A manifest may therefore mix real and
synthetic cases — every case carries its own ``synthetic`` flag and a
``dataset_role`` tag, so nothing downstream can confuse them.

Real layouts (as written by the download scripts):

    data/raw/kather2016/Kather_texture_2016_image_tiles_5000/<NN_CLASS>/*.tif
    data/raw/pannuke/extracted/fold3/{images,labels,index.csv}
    data/raw/deepliif/<Set folder>/*.png                     six-panel composites
    data/raw/mcmicro_exemplar001/exemplar-001/{markers.csv,raw/*.ome.tiff}
    data/raw/visium_hne/visium_hne_adata.h5ad
"""

from __future__ import annotations

from pathlib import Path

from ...config import ProjectConfig
from ...ledger import RunLedger
from ...manifest import Manifest, save_manifest
from ...schemas import CaseRecord, Modality, Track
from ...storage import Storage
from .io import (
    read_deepliif_composite,
    read_markers_csv,
    read_ome_tiff,
    read_rgb_tile,
    read_visium_h5ad,
)
from .pannuke import read_index
from .synth import generate_synthetic_he, generate_synthetic_mif, generate_synthetic_spots

KATHER_DIRNAME = "kather2016"
KATHER_MPP = 0.495
PANNUKE_DIRNAME = "pannuke"
DEEPLIIF_DIRNAME = "deepliif"
MCMICRO_DIRNAME = "mcmicro_exemplar001"
VISIUM_DIRNAME = "visium_hne"
SYNTHETIC_DIRNAME = "synthetic_pathology"


def _key(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


# ---------------------------------------------------------------------------
# Real-data readers per role: each returns a list of CaseRecord
# ---------------------------------------------------------------------------


def kather_cases(raw_dir: Path, base: Path, limit: int | None) -> list[CaseRecord]:
    root = raw_dir / KATHER_DIRNAME
    tiles = sorted(p for p in root.rglob("*.tif") if not p.name.startswith("._"))
    cases = []
    for path in tiles[:limit] if limit else tiles:
        tissue_class = path.parent.name.split("_", 1)[-1]  # "01_TUMOR" → "TUMOR"
        _, geometry = read_rgb_tile(path, KATHER_MPP, stain="HE", magnification=20.0)
        cases.append(
            CaseRecord(
                case_id=f"kather_{tissue_class.lower()}_{path.stem}",
                track=Track.PATHOLOGY,
                image_key=_key(path, base),
                modality=Modality.HE,
                geometry=geometry,
                source="kather2016 (zenodo 53169)",
                tags={"dataset_role": "tissue", "tissue_class": tissue_class},
            )
        )
    return cases


def pannuke_cases(raw_dir: Path, base: Path, limit: int | None) -> list[CaseRecord]:
    root = raw_dir / PANNUKE_DIRNAME / "extracted"
    rows = []
    for fold_dir in sorted(root.glob("fold*")) if root.exists() else []:
        rows += [(fold_dir, r) for r in read_index(root, fold_dir.name)]
    cases = []
    for fold_dir, row in rows[:limit] if limit else rows:
        image_path = fold_dir / "images" / f"{row['case_id']}.png"
        label_path = fold_dir / "labels" / f"{row['case_id']}.npz"
        _, geometry = read_rgb_tile(image_path, 0.25, stain="HE", magnification=40.0)
        cases.append(
            CaseRecord(
                case_id=row["case_id"],
                track=Track.PATHOLOGY,
                image_key=_key(image_path, base),
                label_key=_key(label_path, base),
                modality=Modality.HE,
                geometry=geometry,
                source="pannuke (RationAI mirror, CC-BY-NC-SA 4.0)",
                tags={
                    "dataset_role": "nuclei",
                    "tissue_type": row["tissue"],
                    "n_nuclei": row["n_nuclei"],
                    "licence": "CC-BY-NC-SA-4.0",
                },
            )
        )
    return cases


def deepliif_cases(raw_dir: Path, base: Path, limit: int | None) -> list[CaseRecord]:
    root = raw_dir / DEEPLIIF_DIRNAME
    files = sorted(p for p in root.rglob("*.png") if not p.name.startswith("._"))
    cases = []
    for path in files[:limit] if limit else files:
        _, geometry = read_deepliif_composite(path)
        key = _key(path, base)
        cases.append(
            CaseRecord(
                case_id=f"deepliif_{path.stem}",
                track=Track.PATHOLOGY,
                image_key=key,
                label_key=key,
                modality=Modality.IHC,
                geometry=geometry,
                source="DeepLIIF (zenodo 4751737, CC-BY 4.0)",
                tags={
                    "dataset_role": "ihc",
                    "label_panel": "Seg",
                    "panels": ",".join(geometry.channels),
                },
            )
        )
    return cases


def mcmicro_cases(
    raw_dir: Path, base: Path, limit: int | None, default_mpp: float
) -> list[CaseRecord]:
    root = raw_dir / MCMICRO_DIRNAME
    markers_files = list(root.rglob("markers.csv"))
    if not markers_files:
        return []
    markers = read_markers_csv(markers_files[0])
    ome_files = sorted(p for p in root.rglob("*.ome.tif*") if not p.name.startswith("._"))
    try:
        import tifffile
    except ImportError:  # pragma: no cover
        return []
    cases = []
    for cycle_index, path in enumerate(ome_files):
        with tifffile.TiffFile(str(path)) as tif:
            n_series = len(tif.series)
        for series in range(n_series):
            data, geometry = read_ome_tiff(
                path, series=series, channel_names=None, default_microns_per_pixel=default_mpp
            )
            n_channels = data.shape[0]
            names = (
                markers[cycle_index * n_channels : (cycle_index + 1) * n_channels]
                or geometry.channels
            )
            geometry = geometry.model_copy(update={"channels": list(names), "tile_x": series})
            cases.append(
                CaseRecord(
                    case_id=f"mcmicro_{path.stem.replace('.ome', '')}_tile{series:02d}",
                    track=Track.PATHOLOGY,
                    image_key=_key(path, base),
                    modality=Modality.MIF,
                    geometry=geometry,
                    source="MCMICRO exemplar-001 (labsyspharm)",
                    tags={
                        "dataset_role": "mif",
                        "cycle": str(cycle_index),
                        "series": str(series),
                        "registered": "no",
                    },
                )
            )
            if limit and len(cases) >= limit:
                return cases
    return cases


def visium_cases(raw_dir: Path, base: Path) -> list[CaseRecord]:
    root = raw_dir / VISIUM_DIRNAME
    files = sorted(root.glob("*.h5ad")) if root.exists() else []
    cases = []
    for path in files:
        adata, _, geometry = read_visium_h5ad(path)
        cases.append(
            CaseRecord(
                case_id=f"visium_{path.stem}",
                track=Track.PATHOLOGY,
                image_key=_key(path, base),
                modality=Modality.SPATIAL_TRANSCRIPTOMICS,
                geometry=geometry,
                source="10x Visium sample via squidpy",
                tags={
                    "dataset_role": "spatial",
                    "n_spots": str(adata.n_obs),
                    "n_genes": str(adata.n_vars),
                },
            )
        )
    return cases


# ---------------------------------------------------------------------------
# Synthetic cases per role
# ---------------------------------------------------------------------------


def synthetic_cases(
    role: str, out_dir: Path, base: Path, n_tiles: int, seed: int
) -> list[CaseRecord]:
    common = {
        "track": Track.PATHOLOGY,
        "modality": Modality.SYNTHETIC,
        "synthetic": True,
        "source": "tracks.pathology.synth",
    }
    if role in ("tissue", "nuclei"):
        records = generate_synthetic_he(out_dir / "he", n_tiles, seed)
        return [
            CaseRecord(
                case_id=f"{r['case_id']}_{role}",
                image_key=_key(r["image_path"], base),
                label_key=_key(r["label_path"], base) if role == "nuclei" else None,
                geometry=r["geometry"],
                tags={"dataset_role": role, "tissue_class": r["tissue_class"]},
                **common,
            )
            for r in records
        ]
    if role in ("ihc", "mif"):
        records = generate_synthetic_mif(out_dir / "mif", max(1, n_tiles // 4), seed)
        cases = []
        for r in records:
            if role == "mif":
                cases.append(
                    CaseRecord(
                        case_id=f"{r['case_id']}_mif",
                        image_key=_key(r["ome_path"], base),
                        label_key=_key(r["label_path"], base),
                        geometry=r["geometry"],
                        tags={"dataset_role": "mif", "registered": "yes"},
                        **common,
                    )
                )
            else:
                g = r["geometry"].model_copy(
                    update={
                        "channels": ["IHC", "Hematoxylin", "DAPI", "Lap2", "Marker", "Seg"],
                        "stain": "IHC+mIF",
                    }
                )
                key = _key(r["composite_path"], base)
                cases.append(
                    CaseRecord(
                        case_id=f"{r['case_id']}_ihc",
                        image_key=key,
                        label_key=key,
                        geometry=g,
                        tags={"dataset_role": "ihc", "label_panel": "Seg"},
                        **common,
                    )
                )
        return cases
    if role == "spatial":
        r = generate_synthetic_spots(out_dir / "spots", seed)
        return [
            CaseRecord(
                case_id=r["case_id"],
                image_key=_key(r["path"], base),
                geometry=r["geometry"],
                tags={"dataset_role": "spatial", "n_spots": str(r["n_spots"])},
                **common,
            )
        ]
    raise ValueError(f"Unknown dataset role {role!r}")


# ---------------------------------------------------------------------------
# The entry point
# ---------------------------------------------------------------------------


def ingest_pathology(
    cfg: ProjectConfig,
    storage: Storage,
    ledger: RunLedger,
    *,
    synthetic: bool | None = None,
    limit: int | None = None,
    roles: list[str] | None = None,
) -> tuple[Manifest, str]:
    """Build and save the pathology manifest. Returns (manifest, storage key)."""
    track_cfg = cfg.require_track("pathology")
    base = Path(cfg.storage.base_dir)
    raw_dir = base / cfg.paths.raw
    synth_dir = raw_dir / SYNTHETIC_DIRNAME
    wanted = roles or [d.role for d in track_cfg.datasets if d.enabled]
    readers = {
        "tissue": lambda: kather_cases(raw_dir, base, limit),
        "nuclei": lambda: pannuke_cases(raw_dir, base, limit),
        "ihc": lambda: deepliif_cases(raw_dir, base, limit),
        "mif": lambda: mcmicro_cases(raw_dir, base, limit, track_cfg.mif_default_microns_per_pixel),
        "spatial": lambda: visium_cases(raw_dir, base),
    }
    record = ledger.start("ingest", cfg, track=Track.PATHOLOGY, notes=",".join(wanted))
    cases: list[CaseRecord] = []
    used: list[str] = []
    for role in wanted:
        entry = track_cfg.dataset(role)
        real: list[CaseRecord] = [] if synthetic else readers[role]()
        if real and synthetic is not True:
            cases += real
            used.append(entry.name if entry else role)
            continue
        if synthetic is False:
            raise FileNotFoundError(
                f"No real data for role {role!r} under {raw_dir}; run the matching scripts/download_*.py"
            )
        if not track_cfg.use_synthetic_fallback and synthetic is None:
            raise FileNotFoundError(
                f"No real data for role {role!r} and the synthetic fallback is disabled"
            )
        n = min(track_cfg.synthetic_tiles, limit) if limit else track_cfg.synthetic_tiles
        cases += synthetic_cases(role, synth_dir, base, n, track_cfg.seed)
        used.append(f"synthetic:{role}")
    all_synthetic = bool(cases) and all(c.synthetic for c in cases)
    manifest = Manifest(
        track=Track.PATHOLOGY,
        dataset=",".join(used) or "none",
        synthetic=all_synthetic,
        run_id=record.run_id,
        cases=cases,
    )
    key = save_manifest(storage, manifest, cfg.paths.processed.as_posix())
    ledger.finish(record, notes=f"{len(cases)} cases → {key}")
    return manifest, key

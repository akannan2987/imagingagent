"""Ingestion for the mri track: find the cases, read their geometry, write
the manifest.

Two sources, one output:

- **Real data** — the Medical Segmentation Decathlon layout under
  ``data/raw/msd_task04/`` (``imagesTr/``, ``labelsTr/``, ``imagesTs/``),
  as written by ``scripts/download_msd_hippocampus.py``.
- **Synthetic fallback** — generated on the spot under
  ``data/raw/synthetic_mri/`` when the real data is absent and the config
  allows it, or when ``--synthetic`` is asked for explicitly.

Either way each case is opened once, its geometry read and asserted, and a
``CaseRecord`` written to the manifest. Nothing in ``data/raw/`` is
modified.
"""

from __future__ import annotations

from pathlib import Path

from ...config import ProjectConfig
from ...ledger import RunLedger
from ...manifest import Manifest, save_manifest
from ...schemas import CaseRecord, Modality, Track
from ...storage import Storage
from .io import read_nifti
from .synth import generate_synthetic_volumes

MSD_DIRNAME = "msd_task04"
SYNTHETIC_DIRNAME = "synthetic_mri"


def _to_key(path: Path, base: Path) -> str:
    """A storage key (forward slashes) for a path under the storage root."""
    return path.resolve().relative_to(base.resolve()).as_posix()


def msd_cases(msd_dir: Path) -> list[tuple[str, Path, Path | None]]:
    """(case_id, image_path, label_path) for every MSD image; labels only in imagesTr.

    MSD names files ``hippocampus_001.nii.gz``; hidden files starting with
    ``._`` (macOS archive artefacts) are skipped.
    """
    found: list[tuple[str, Path, Path | None]] = []
    for split in ("imagesTr", "imagesTs"):
        folder = msd_dir / split
        if not folder.is_dir():
            continue
        for image_path in sorted(folder.glob("*.nii.gz")):
            if image_path.name.startswith("._"):
                continue
            case_id = image_path.name.replace(".nii.gz", "")
            label_path = msd_dir / "labelsTr" / image_path.name if split == "imagesTr" else None
            found.append(
                (case_id, image_path, label_path if label_path and label_path.exists() else None)
            )
    return found


def ingest_mri(
    cfg: ProjectConfig,
    storage: Storage,
    ledger: RunLedger,
    *,
    synthetic: bool | None = None,
    limit: int | None = None,
) -> tuple[Manifest, str]:
    """Build and save the mri manifest. Returns (manifest, storage key).

    ``synthetic=None`` means: use real data if present, else fall back if
    the config allows. ``limit`` caps the number of cases (useful for a
    quick first run).
    """
    track_cfg = cfg.require_track("mri")
    base = Path(cfg.storage.base_dir)
    raw_dir = base / cfg.paths.raw
    msd_dir = raw_dir / MSD_DIRNAME
    have_real = msd_dir.is_dir() and bool(msd_cases(msd_dir))

    if synthetic is None:
        synthetic = not have_real
    if synthetic and not track_cfg.dataset.use_synthetic_fallback and not have_real:
        raise FileNotFoundError(
            f"No real data under {msd_dir} and the synthetic fallback is disabled. "
            "Run scripts/download_msd_hippocampus.py or enable tracks.mri.dataset.use_synthetic_fallback."
        )

    record = ledger.start(
        "ingest", cfg, track=Track.MRI, notes="synthetic" if synthetic else track_cfg.dataset.name
    )
    cases: list[CaseRecord] = []

    if synthetic:
        out_dir = raw_dir / SYNTHETIC_DIRNAME
        n = (
            min(track_cfg.dataset.synthetic_cases, limit)
            if limit
            else track_cfg.dataset.synthetic_cases
        )
        for case_id, image_path, label_path, geometry in generate_synthetic_volumes(
            out_dir, n, track_cfg.dataset.seed
        ):
            cases.append(
                CaseRecord(
                    case_id=case_id,
                    track=Track.MRI,
                    image_key=_to_key(image_path, base),
                    label_key=_to_key(label_path, base),
                    modality=Modality.SYNTHETIC,
                    geometry=geometry,
                    synthetic=True,
                    source="scripts/synth (tracks.mri.synth)",
                )
            )
        dataset_name = "synthetic"
    else:
        entries = msd_cases(msd_dir)
        if limit:
            entries = entries[:limit]
        for case_id, image_path, label_path in entries:
            _, geometry = read_nifti(image_path)  # read once; assert geometry is sane
            cases.append(
                CaseRecord(
                    case_id=case_id,
                    track=Track.MRI,
                    image_key=_to_key(image_path, base),
                    label_key=_to_key(label_path, base) if label_path else None,
                    modality=Modality.MRI,
                    geometry=geometry,
                    synthetic=False,
                    source=f"{track_cfg.dataset.name} ({track_cfg.dataset.source_url})",
                )
            )
        dataset_name = track_cfg.dataset.name

    manifest = Manifest(
        track=Track.MRI,
        dataset=dataset_name,
        synthetic=synthetic,
        run_id=record.run_id,
        cases=cases,
    )
    key = save_manifest(storage, manifest, cfg.paths.processed.as_posix())
    ledger.finish(record, notes=f"{len(cases)} cases → {key}")
    return manifest, key

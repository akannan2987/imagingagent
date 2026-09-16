"""mri track, Phase 1: readers keep geometry; synthetic data; the manifest.

Every test here needs nibabel and SimpleITK (requirements-mri.txt) and
skips itself cleanly when they are absent, so the core suite still runs on
a bare install.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from imagingagent.config import ProjectConfig
from imagingagent.ledger import RunLedger
from imagingagent.manifest import load_manifest, manifest_key
from imagingagent.schemas import Modality, Track, VolumeGeometry
from imagingagent.storage import LocalStorage

nib = pytest.importorskip("nibabel", reason="requirements-mri.txt not installed")
sitk = pytest.importorskip("SimpleITK", reason="requirements-mri.txt not installed")

from imagingagent.tracks.mri.ingest import ingest_mri, msd_cases
from imagingagent.tracks.mri.io import (
    geometry_from_affine,
    read_dicom_series,
    read_nifti,
    write_nifti,
)
from imagingagent.tracks.mri.synth import (
    SyntheticVolumeSpec,
    generate_synthetic_volumes,
    make_case,
    write_synthetic_dicom_series,
)

pytestmark = pytest.mark.mri


def test_geometry_from_affine_reads_spacing_orientation_origin() -> None:
    affine = np.diag([1.0, 1.0, 1.2, 1.0])
    affine[:3, 3] = (-10.0, 5.0, 2.5)
    g = geometry_from_affine(affine, (10, 20, 30))
    assert g.spacing_mm == (1.0, 1.0, 1.2)
    assert g.orientation == "RAS"
    assert g.origin_mm == (-10.0, 5.0, 2.5)
    assert g.shape == (10, 20, 30)


def test_nifti_round_trip_preserves_geometry(tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype=np.float32).reshape(2, 3, 4)
    geometry = VolumeGeometry(
        spacing_mm=(0.5, 1.0, 2.0), shape=(2, 3, 4), origin_mm=(1.0, 2.0, 3.0)
    )
    path = write_nifti(data, geometry, tmp_path / "x.nii.gz")
    again, g = read_nifti(path)
    np.testing.assert_array_equal(again, data)
    assert g.spacing_mm == geometry.spacing_mm
    assert g.origin_mm == geometry.origin_mm
    assert g.orientation == "RAS"


def test_read_nifti_rejects_4d(tmp_path: Path) -> None:
    nib.save(
        nib.Nifti1Image(np.zeros((2, 2, 2, 3), dtype=np.float32), np.eye(4)),
        str(tmp_path / "4d.nii.gz"),
    )
    with pytest.raises(ValueError, match="3D"):
        read_nifti(tmp_path / "4d.nii.gz")


def test_synthetic_case_is_reproducible_and_plausible() -> None:
    spec = SyntheticVolumeSpec()
    a = make_case(np.random.default_rng(7), spec)
    b = make_case(np.random.default_rng(7), spec)
    np.testing.assert_array_equal(a[0], b[0])
    image, label, geometry = a
    assert image.shape == spec.shape and label.shape == spec.shape
    assert 0.0 <= image.min() and image.max() <= 1.0
    volume = geometry.volume_mm3(int(label.sum()))
    assert 800 < volume < 7000  # a hippocampus-sized blob
    assert image[label == 1].mean() > image[label == 0].mean()  # blob brighter than background


def test_dicom_series_round_trip(tmp_path: Path) -> None:
    image, _, geometry = make_case(
        np.random.default_rng(3), SyntheticVolumeSpec(shape=(12, 14, 10))
    )
    folder = write_synthetic_dicom_series(image, geometry, tmp_path / "dcm")
    assert len(list(folder.glob("*.dcm"))) == 10
    again, g = read_dicom_series(folder)
    assert again.shape == (12, 14, 10)
    assert g.spacing_mm == pytest.approx(geometry.spacing_mm)
    assert g.orientation == "LPS"  # DICOM's native frame; canonicalised in Phase 2
    assert np.corrcoef(image.ravel(), again.ravel())[0, 1] > 0.99


def test_read_dicom_series_empty_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_dicom_series(tmp_path)


def _config(tmp_path: Path, **dataset_overrides) -> ProjectConfig:
    cfg = ProjectConfig()
    dataset = cfg.tracks.mri.dataset.model_copy(update={"synthetic_cases": 4, **dataset_overrides})
    tracks = cfg.tracks.model_copy(
        update={"mri": cfg.tracks.mri.model_copy(update={"dataset": dataset})}
    )
    paths = cfg.paths.model_copy(
        update={"raw": Path("data/raw"), "processed": Path("data/processed")}
    )
    return cfg.model_copy(
        update={
            "tracks": tracks,
            "paths": paths,
            "storage": cfg.storage.model_copy(update={"base_dir": tmp_path}),
        }
    )


def test_ingest_synthetic_writes_manifest_and_ledger(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    storage = LocalStorage(tmp_path)
    ledger = RunLedger(storage)
    manifest, key = ingest_mri(cfg, storage, ledger)
    assert key == manifest_key(Track.MRI)
    assert manifest.synthetic and manifest.dataset == "synthetic"
    assert len(manifest) == 4 and len(manifest.with_labels()) == 4
    case = manifest.cases[0]
    assert case.track is Track.MRI and case.modality is Modality.SYNTHETIC and case.synthetic
    assert case.geometry is not None and case.geometry.kind == "volume"
    assert storage.exists(case.image_key) and storage.exists(case.label_key)
    loaded = load_manifest(storage, "mri")
    assert loaded.case_ids == manifest.case_ids
    statuses = [r.status for r in ledger.latest_per_run().values()]
    assert statuses == ["finished"]


def test_ingest_limit_and_forced_synthetic(tmp_path: Path) -> None:
    manifest, _ = ingest_mri(
        _config(tmp_path),
        LocalStorage(tmp_path),
        RunLedger(LocalStorage(tmp_path)),
        synthetic=True,
        limit=2,
    )
    assert len(manifest) == 2


def test_ingest_refuses_when_fallback_disabled_and_no_real_data(tmp_path: Path) -> None:
    cfg = _config(tmp_path, use_synthetic_fallback=False)
    with pytest.raises(FileNotFoundError, match="synthetic fallback is disabled"):
        ingest_mri(cfg, LocalStorage(tmp_path), RunLedger(LocalStorage(tmp_path)))


def test_ingest_reads_real_msd_layout(tmp_path: Path) -> None:
    """Fake the MSD folder layout with synthetic volumes and ingest it as 'real'."""
    msd = tmp_path / "data" / "raw" / "msd_task04"
    written = generate_synthetic_volumes(msd, 3, seed=11)
    # rename to MSD-style ids and add an unlabelled test image + a macOS junk file
    for i, (_case_id, image_path, label_path, _) in enumerate(written, start=1):
        image_path.rename(msd / "imagesTr" / f"hippocampus_{i:03d}.nii.gz")
        label_path.rename(msd / "labelsTr" / f"hippocampus_{i:03d}.nii.gz")
    (msd / "imagesTs").mkdir()
    (msd / "imagesTr" / "hippocampus_001.nii.gz").replace(
        msd / "imagesTs" / "hippocampus_900.nii.gz"
    )
    (msd / "labelsTr" / "hippocampus_001.nii.gz").unlink()
    (msd / "imagesTr" / "._hippocampus_002.nii.gz").write_bytes(b"junk")
    assert [c[0] for c in msd_cases(msd)] == [
        "hippocampus_002",
        "hippocampus_003",
        "hippocampus_900",
    ]

    manifest, _ = ingest_mri(
        _config(tmp_path), LocalStorage(tmp_path), RunLedger(LocalStorage(tmp_path))
    )
    assert not manifest.synthetic and manifest.dataset == "msd_task04_hippocampus"
    assert len(manifest) == 3 and len(manifest.with_labels()) == 2
    assert all(c.modality is Modality.MRI for c in manifest.cases)

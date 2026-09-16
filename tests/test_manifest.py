"""Shared manifest contract: save, load, filter."""

from __future__ import annotations

import pytest

from imagingagent.manifest import Manifest, load_manifest, manifest_key, save_manifest
from imagingagent.schemas import CaseRecord, Modality, TileGeometry, Track, VolumeGeometry
from imagingagent.storage import LocalStorage


def test_manifest_round_trip_both_tracks(storage: LocalStorage) -> None:
    mri = Manifest(
        track=Track.MRI,
        dataset="synthetic",
        synthetic=True,
        cases=[
            CaseRecord(
                case_id="a",
                track=Track.MRI,
                image_key="a.nii.gz",
                label_key="a_lab.nii.gz",
                modality=Modality.SYNTHETIC,
                geometry=VolumeGeometry(spacing_mm=(1, 1, 1), shape=(2, 2, 2)),
                synthetic=True,
            ),
            CaseRecord(
                case_id="b",
                track=Track.MRI,
                image_key="b.nii.gz",
                modality=Modality.SYNTHETIC,
                geometry=VolumeGeometry(spacing_mm=(1, 1, 1), shape=(2, 2, 2)),
                synthetic=True,
            ),
        ],
    )
    path = Manifest(
        track=Track.PATHOLOGY,
        dataset="kather2016",
        cases=[
            CaseRecord(
                case_id="k",
                track=Track.PATHOLOGY,
                image_key="k.tif",
                modality=Modality.HE,
                geometry=TileGeometry(microns_per_pixel=0.495, width=150, height=150),
            )
        ],
    )
    assert save_manifest(storage, mri) == manifest_key("mri") == "data/processed/manifest_mri.json"
    save_manifest(storage, path)
    assert load_manifest(storage, Track.MRI).case_ids == ["a", "b"]
    assert len(load_manifest(storage, "pathology")) == 1
    assert [c.case_id for c in load_manifest(storage, "mri").with_labels()] == ["a"]


def test_missing_manifest_says_how_to_make_one(storage: LocalStorage) -> None:
    with pytest.raises(FileNotFoundError, match="imagingagent ingest --track mri"):
        load_manifest(storage, "mri")

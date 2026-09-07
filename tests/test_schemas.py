"""Data contracts: they validate, serialise and publish a schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from imagingagent.schemas import (
    AuditReport,
    CaseRecord,
    Finding,
    Modality,
    TileGeometry,
    Track,
    Verdict,
    VolumeGeometry,
)


def test_case_record_round_trip() -> None:
    """Updated in Phase 0c: spacing now lives inside a VolumeGeometry."""
    case = CaseRecord(
        case_id="c001",
        track=Track.MRI,
        image_key="data/raw/c001.nii.gz",
        geometry=VolumeGeometry(spacing_mm=(1.0, 1.0, 1.0), shape=(35, 50, 35)),
    )
    again = CaseRecord.model_validate_json(case.model_dump_json())
    assert again == case
    assert again.modality is Modality.MRI
    assert again.spacing_mm == (1.0, 1.0, 1.0)  # convenience property still works
    assert again.shape == (35, 50, 35)


def test_volume_geometry_converts_voxels_to_mm3() -> None:
    geometry = VolumeGeometry(spacing_mm=(1.0, 1.0, 1.2), shape=(10, 10, 10))
    assert geometry.voxel_volume_mm3 == pytest.approx(1.2)
    assert geometry.volume_mm3(2500) == pytest.approx(3000.0)
    with pytest.raises(ValidationError):
        VolumeGeometry(spacing_mm=(1.0, 0.0, 1.0), shape=(10, 10, 10))


def test_tile_geometry_converts_pixels_to_mm2() -> None:
    geometry = TileGeometry(
        microns_per_pixel=0.5, width=150, height=150, channels=["R", "G", "B"], stain="HE"
    )
    assert geometry.pixel_area_um2 == pytest.approx(0.25)
    assert geometry.tile_area_mm2 == pytest.approx(0.005625)
    case = CaseRecord(
        case_id="k1",
        track=Track.PATHOLOGY,
        image_key="k1.tif",
        modality=Modality.HE,
        geometry=geometry,
    )
    assert case.shape == (150, 150)
    assert case.spacing_mm is None


def test_track_and_modality_must_agree() -> None:
    with pytest.raises(ValidationError, match="belongs to track"):
        CaseRecord(case_id="x", track=Track.MRI, image_key="x.tif", modality=Modality.HE)
    with pytest.raises(ValidationError, match="expects"):
        CaseRecord(
            case_id="x",
            track=Track.MRI,
            image_key="x.nii.gz",
            modality=Modality.MRI,
            geometry=TileGeometry(microns_per_pixel=0.5, width=10, height=10),
        )
    with pytest.raises(ValidationError, match="specific track"):
        CaseRecord(case_id="x", track=Track.SHARED, image_key="x")


def test_synthetic_modality_works_on_either_track() -> None:
    mri = CaseRecord(
        case_id="s1",
        track=Track.MRI,
        image_key="s1.nii.gz",
        modality=Modality.SYNTHETIC,
        geometry=VolumeGeometry(spacing_mm=(1, 1, 1), shape=(8, 8, 8)),
        synthetic=True,
    )
    tile = CaseRecord(
        case_id="s2",
        track=Track.PATHOLOGY,
        image_key="s2.tif",
        modality=Modality.SYNTHETIC,
        geometry=TileGeometry(microns_per_pixel=0.5, width=8, height=8),
        synthetic=True,
    )
    assert mri.synthetic and tile.synthetic


def test_geometry_discriminator_round_trips_both_kinds() -> None:
    for geometry in (
        VolumeGeometry(spacing_mm=(1, 1, 1), shape=(2, 2, 2)),
        TileGeometry(microns_per_pixel=0.25, width=4, height=4),
    ):
        track = Track.MRI if geometry.kind == "volume" else Track.PATHOLOGY
        modality = Modality.MRI if geometry.kind == "volume" else Modality.HE
        case = CaseRecord(
            case_id="g", track=track, image_key="g", modality=modality, geometry=geometry
        )
        again = CaseRecord.model_validate_json(case.model_dump_json())
        assert type(again.geometry) is type(geometry)


def test_audit_report_failed_findings_and_schema() -> None:
    report = AuditReport(
        run_id="r1",
        case_id="c001",
        track=Track.MRI,
        findings=[
            Finding(name="volume_mm3", value=3200.0, unit="mm3", passed=True),
            Finding(name="components", value=3.0, unit="count", passed=False, message="fragmented"),
        ],
        score=0.42,
        verdict=Verdict.REVIEW,
    )
    assert [f.name for f in report.failed_findings()] == ["components"]
    schema = AuditReport.model_json_schema()
    assert "findings" in schema["properties"]
    assert schema["properties"]["track"]["default"] == "shared"


def test_score_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AuditReport(run_id="r", case_id="c", score=1.5)

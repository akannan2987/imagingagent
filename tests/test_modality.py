"""Modality registry: every modality knows its track, geometry and status."""

from __future__ import annotations

import pytest

from imagingagent.modality import REGISTRY, implemented, spec_for, specs_for_track
from imagingagent.schemas import Modality, Track


def test_every_enum_modality_is_registered_and_consistent() -> None:
    for modality in Modality:
        spec = spec_for(modality)
        assert spec.modality is modality
        assert spec.status == "implemented"


def test_registry_has_planned_modalities_for_the_roadmap() -> None:
    planned = {name for name, spec in REGISTRY.items() if spec.status == "planned"}
    assert {"PET", "DXA", "ULTRASOUND", "OPHTHALMIC", "CT", "XENIUM"} <= planned
    assert all(
        spec.modality is None or spec.modality is Modality.CT
        for spec in REGISTRY.values()
        if spec.status == "planned"
    )


def test_specs_for_track_puts_implemented_first() -> None:
    specs = specs_for_track(Track.PATHOLOGY)
    statuses = [s.status for s in specs]
    assert statuses == sorted(statuses, key=lambda s: s != "implemented")
    assert all(s.track in (Track.PATHOLOGY, Track.SHARED) for s in specs)
    assert all(s.status == "implemented" for s in specs_for_track("mri", include_planned=False))


def test_unknown_modality_fails_loudly() -> None:
    with pytest.raises(KeyError, match="Unknown modality"):
        spec_for("HOLOGRAM")


def test_implemented_geometry_matches_track() -> None:
    for spec in implemented():
        if spec.track is Track.MRI:
            assert spec.geometry == "volume"
        elif spec.track is Track.PATHOLOGY:
            assert spec.geometry == "tile"

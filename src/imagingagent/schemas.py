"""Data contracts: the shapes every layer agrees on.

Think of these as customs forms. A case, a finding, a report — each must be
filled in correctly before it can cross from one layer to the next, and the
same forms are what a future HTTP or MCP server hands to callers. Because
they are Pydantic models they validate themselves, serialise to JSON, and can
publish their own JSON Schema (``AuditReport.model_json_schema()``), which is
exactly what agent tooling needs to know how to call us.

Two modality families share these contracts. What differs between a scan
and a slide is *geometry* — the note that turns pixel counts into
millimetres — so geometry is a union of two shapes, ``VolumeGeometry`` and
``TileGeometry``, and every other contract carries a ``track``.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Track(StrEnum):
    """Which modality family a record belongs to."""

    MRI = "mri"
    PATHOLOGY = "pathology"
    SHARED = "shared"  # runs and reports that span both


class Modality(StrEnum):
    """Imaging modality. Implemented modalities only; planned ones live in the
    modality registry (``modality.py``) so the roadmap is visible in code."""

    MRI = "MRI"
    HE = "HE"  # haematoxylin and eosin brightfield
    IHC = "IHC"  # immunohistochemistry brightfield
    MIF = "MIF"  # multiplex immunofluorescence
    SPATIAL_TRANSCRIPTOMICS = "SPATIAL_TRANSCRIPTOMICS"
    SYNTHETIC = "SYNTHETIC"


# ---------------------------------------------------------------------------
# Geometry — one shape per modality family
# ---------------------------------------------------------------------------


class VolumeGeometry(BaseModel):
    """How a 3D volume maps to the real world.

    ``spacing_mm`` is the size of one voxel along each axis; ``orientation``
    says which way the axes point in the patient (RAS = x→Right, y→Anterior,
    z→Superior); ``origin_mm`` is where voxel (0,0,0) sits in the scanner.
    Lose any of these and every volume measurement is silently wrong.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["volume"] = "volume"
    spacing_mm: tuple[float, float, float]
    shape: tuple[int, int, int]
    orientation: str = Field(default="RAS", min_length=3, max_length=3)
    origin_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)

    @model_validator(mode="after")
    def _positive(self) -> VolumeGeometry:
        if any(s <= 0 for s in self.spacing_mm):
            raise ValueError("spacing_mm values must be positive")
        if any(n <= 0 for n in self.shape):
            raise ValueError("shape values must be positive")
        return self

    @property
    def voxel_volume_mm3(self) -> float:
        a, b, c = self.spacing_mm
        return a * b * c

    def volume_mm3(self, voxel_count: int) -> float:
        """Convert a voxel count into cubic millimetres."""
        return voxel_count * self.voxel_volume_mm3


class TileGeometry(BaseModel):
    """How a 2D tile maps to the slide and the real world.

    ``microns_per_pixel`` is the slide's scale bar (0.25 µm at 40×, ~0.5 µm
    at 20×); ``level`` is the pyramid zoom the tile was read from; ``tile_x``
    and ``tile_y`` locate it on the slide at that level; ``channels`` names
    the colour layers (RGB for brightfield, marker names for fluorescence).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tile"] = "tile"
    microns_per_pixel: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    level: int = Field(default=0, ge=0)
    tile_x: int = Field(default=0, ge=0)
    tile_y: int = Field(default=0, ge=0)
    magnification: float | None = Field(default=None, gt=0)
    channels: list[str] = Field(default_factory=list)
    stain: str | None = None

    @property
    def pixel_area_um2(self) -> float:
        return self.microns_per_pixel**2

    @property
    def tile_area_mm2(self) -> float:
        """Area of the whole tile in square millimetres (1 mm² = 1e6 µm²)."""
        return self.width * self.height * self.pixel_area_um2 / 1e6

    def area_mm2(self, pixel_count: int) -> float:
        """Convert a pixel count into square millimetres."""
        return pixel_count * self.pixel_area_um2 / 1e6


Geometry = Annotated[VolumeGeometry | TileGeometry, Field(discriminator="kind")]


# ---------------------------------------------------------------------------
# Cases, findings, reports, runs
# ---------------------------------------------------------------------------


class CaseRecord(BaseModel):
    """One subject/scan or one slide/tile as the pipeline sees it."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(description="Stable identifier, e.g. 'hippocampus_001' or 'kather_0421'.")
    track: Track = Field(description="Which modality family this case belongs to.")
    image_key: str = Field(description="Storage key of the image (NIfTI, TIFF, ...).")
    label_key: str | None = Field(
        default=None, description="Storage key of a reference label map, if any."
    )
    modality: Modality = Modality.MRI
    geometry: Geometry | None = Field(default=None, description="VolumeGeometry or TileGeometry.")
    synthetic: bool = Field(default=False, description="True when generated, not acquired.")
    source: str = Field(default="", description="Where the case came from (dataset name, URL).")

    @model_validator(mode="after")
    def _consistent(self) -> CaseRecord:
        from .modality import spec_for  # local import: modality.py imports this module

        if self.track is Track.SHARED:
            raise ValueError("A case belongs to a specific track, not 'shared'")
        spec = spec_for(self.modality)
        if spec.track is not Track.SHARED and spec.track is not self.track:
            raise ValueError(
                f"Modality {self.modality.value} belongs to track {spec.track.value!r}, "
                f"not {self.track.value!r}"
            )
        expected = (
            spec.geometry
            if spec.track is not Track.SHARED
            else ("volume" if self.track is Track.MRI else "tile")
        )
        if self.geometry is not None and self.geometry.kind != expected:
            raise ValueError(
                f"Modality {self.modality.value} on track {self.track.value!r} expects "
                f"{expected!r} geometry, got {self.geometry.kind!r}"
            )
        return self

    @property
    def spacing_mm(self) -> tuple[float, float, float] | None:
        """Voxel spacing for volumes; None for tiles."""
        return self.geometry.spacing_mm if isinstance(self.geometry, VolumeGeometry) else None

    @property
    def shape(self) -> tuple[int, ...] | None:
        """Voxels along each axis (volumes) or (height, width) for tiles."""
        if isinstance(self.geometry, VolumeGeometry):
            return self.geometry.shape
        if isinstance(self.geometry, TileGeometry):
            return (self.geometry.height, self.geometry.width)
        return None


class Verdict(StrEnum):
    """The audit's decision for one case."""

    ACCEPT = "accept"  # trustworthy enough to use unreviewed
    REVIEW = "review"  # send to a human within the review budget
    REJECT = "reject"  # implausible; do not use


class Finding(BaseModel):
    """One measured fact about a segmentation and whether it passed."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Short machine name, e.g. 'volume_mm3' or 'nuclei_per_mm2'.")
    value: float | None = Field(default=None, description="Measured value; None if not computable.")
    unit: str = Field(default="", description="Unit of the value, e.g. 'mm3', 'dice', 'per_mm2'.")
    passed: bool | None = Field(
        default=None, description="Whether the check passed; None if informational."
    )
    message: str = Field(default="", description="Plain-language explanation.")
    track: Track | None = Field(default=None, description="Set when a finding is track-specific.")


class AuditReport(BaseModel):
    """The audit result for one case: findings, a score and a verdict."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    case_id: str
    track: Track = Track.SHARED
    findings: list[Finding] = Field(default_factory=list)
    score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Trust score, 1 = fully trusted."
    )
    verdict: Verdict = Verdict.REVIEW
    summary: str = Field(default="", description="One paragraph a non-specialist can read.")

    def failed_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.passed is False]


class RunRecord(BaseModel):
    """One line in the run ledger: who ran what, when, with which settings."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    started_at: str
    command: str
    config_hash: str
    package_version: str
    platform: str
    track: Track = Track.SHARED
    status: str = "started"
    finished_at: str | None = None
    notes: str = ""
    output_dir: Path | None = None

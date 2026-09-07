"""Typed configuration: what a run should do.

Why typed? A YAML file is just text; a typo like ``review_budget_fraction: 10``
(meaning 10 %) would silently flag every case. Pydantic turns the text into
Python objects and checks each value against its declared type and range,
so mistakes fail loudly at load time instead of quietly at 2 a.m.

The configuration has a ``tracks`` block — one entry per modality family
(``mri``, ``pathology``) — so that "which kind of image?" is a first-class,
validated setting rather than an assumption buried in the code.

Precedence (highest first):
    1. an explicit ``--config`` path on the command line
    2. the ``IMAGINGAGENT_CONFIG`` environment variable
    3. the built-in defaults below (identical to ``configs/default.yaml``)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .utils import sha256_bytes

ENV_CONFIG_VAR = "IMAGINGAGENT_CONFIG"

TrackName = Literal["mri", "pathology"]
TRACK_NAMES: tuple[TrackName, ...] = ("mri", "pathology")


# ---------------------------------------------------------------------------
# Shared blocks
# ---------------------------------------------------------------------------


class PathsConfig(BaseModel):
    """Where data and outputs live, relative to the working directory."""

    model_config = ConfigDict(extra="forbid")

    raw: Path = Path("data/raw")
    interim: Path = Path("data/interim")
    processed: Path = Path("data/processed")
    runs: Path = Path("runs")
    models: Path = Path("models")

    def all(self) -> list[Path]:
        """Every managed folder, in creation order."""
        return [self.raw, self.interim, self.processed, self.runs, self.models]


class StorageConfig(BaseModel):
    """Which storage backend to use. Only ``local`` exists today."""

    model_config = ConfigDict(extra="forbid")

    backend: Literal["local"] = "local"
    base_dir: Path = Path(".")


# ---------------------------------------------------------------------------
# mri track
# ---------------------------------------------------------------------------


class MriDatasetConfig(BaseModel):
    """Which volumetric dataset to use and how to stand in for it when absent."""

    model_config = ConfigDict(extra="forbid")

    name: str = "msd_task04_hippocampus"
    modality: str = "MRI"
    source_url: str = "http://medicaldecathlon.com/"
    licence: str = "CC-BY-SA 4.0"
    use_synthetic_fallback: bool = True
    synthetic_cases: int = Field(default=20, ge=1, le=10_000)
    seed: int = Field(default=20260901, ge=0)


class MriTrackConfig(BaseModel):
    """Settings for the volumetric track."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    dataset: MriDatasetConfig = Field(default_factory=MriDatasetConfig)
    target_spacing_mm: tuple[float, float, float] = Field(
        default=(1.0, 1.0, 1.0), description="Voxel size every volume is resampled to."
    )


# ---------------------------------------------------------------------------
# pathology track
# ---------------------------------------------------------------------------

DatasetRole = Literal["tissue", "nuclei", "ihc", "mif", "spatial"]


class PathologyDatasetConfig(BaseModel):
    """One slide-level dataset and the role it plays in the track."""

    model_config = ConfigDict(extra="forbid")

    name: str
    role: DatasetRole
    source_url: str = ""
    licence: str = "recorded at download"
    enabled: bool = True


def _default_pathology_datasets() -> list[PathologyDatasetConfig]:
    return [
        PathologyDatasetConfig(
            name="kather2016",
            role="tissue",
            source_url="https://zenodo.org/records/53169",
            licence="CC-BY 4.0",
        ),
        PathologyDatasetConfig(
            name="pannuke",
            role="nuclei",
            source_url="https://warwick.ac.uk/fac/cross_fac/tia/data/pannuke",
            licence="CC-BY-NC-SA 4.0",
        ),
        PathologyDatasetConfig(
            name="deepliif", role="ihc", source_url="https://zenodo.org/records/4751737"
        ),
        PathologyDatasetConfig(
            name="mcmicro_exemplar001", role="mif", source_url="https://mcmicro.org/"
        ),
        PathologyDatasetConfig(
            name="visium_hne", role="spatial", source_url="https://squidpy.readthedocs.io/"
        ),
    ]


class PathologyTrackConfig(BaseModel):
    """Settings for the slide track."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    datasets: list[PathologyDatasetConfig] = Field(default_factory=_default_pathology_datasets)
    target_microns_per_pixel: float = Field(
        default=0.5, gt=0, description="Resolution every tile is resampled to."
    )
    use_synthetic_fallback: bool = True
    synthetic_tiles: int = Field(default=40, ge=1, le=100_000)
    seed: int = Field(default=20260904, ge=0)

    def dataset(self, role: DatasetRole) -> PathologyDatasetConfig | None:
        """The enabled dataset playing a role, or None."""
        for entry in self.datasets:
            if entry.role == role and entry.enabled:
                return entry
        return None


class TracksConfig(BaseModel):
    """Both tracks. Adding a modality family means adding a field here."""

    model_config = ConfigDict(extra="forbid")

    mri: MriTrackConfig = Field(default_factory=MriTrackConfig)
    pathology: PathologyTrackConfig = Field(default_factory=PathologyTrackConfig)

    def enabled_names(self) -> list[TrackName]:
        return [name for name in TRACK_NAMES if getattr(self, name).enabled]

    def get(self, name: str) -> MriTrackConfig | PathologyTrackConfig:
        """Look a track up by name; unknown names fail loudly."""
        if name not in TRACK_NAMES:
            raise KeyError(f"Unknown track {name!r}; expected one of {TRACK_NAMES}")
        return getattr(self, name)


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


class MriAuditConfig(BaseModel):
    """Plausibility bounds for the volumetric track."""

    model_config = ConfigDict(extra="forbid")

    min_volume_mm3: float = Field(default=1000.0, gt=0)
    max_volume_mm3: float = Field(default=6000.0, gt=0)


class PathologyAuditConfig(BaseModel):
    """Plausibility bounds for the slide track."""

    model_config = ConfigDict(extra="forbid")

    min_nuclei_per_mm2: float = Field(default=50.0, ge=0)
    max_nuclei_per_mm2: float = Field(default=20_000.0, gt=0)


class AuditConfig(BaseModel):
    """The decision the audit serves: a shared review budget, per-track rules."""

    model_config = ConfigDict(extra="forbid")

    review_budget_fraction: float = Field(default=0.10, ge=0.0, le=1.0)
    mri: MriAuditConfig = Field(default_factory=MriAuditConfig)
    pathology: PathologyAuditConfig = Field(default_factory=PathologyAuditConfig)


# ---------------------------------------------------------------------------
# The whole configuration
# ---------------------------------------------------------------------------


class ProjectConfig(BaseModel):
    """The complete, validated configuration for one run."""

    model_config = ConfigDict(extra="forbid")

    project_name: str = "imagingagent"
    paths: PathsConfig = Field(default_factory=PathsConfig)
    tracks: TracksConfig = Field(default_factory=TracksConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    def require_track(self, name: str) -> MriTrackConfig | PathologyTrackConfig:
        """The track's config, or a clear error if it is unknown or disabled."""
        track = self.tracks.get(name)
        if not track.enabled:
            raise ValueError(f"Track {name!r} is disabled in the configuration")
        return track

    def canonical_json(self) -> str:
        """A stable text form: sorted keys, no whitespace games.

        Two configs with the same meaning produce the same string, which is
        what makes the hash below trustworthy.
        """
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def content_hash(self) -> str:
        """Fingerprint of the configuration, recorded in the run ledger."""
        return sha256_bytes(self.canonical_json().encode("utf-8"))


def resolve_config_path(explicit: Path | None = None) -> Path | None:
    """Apply the precedence rules and return the config file to load, if any."""
    if explicit is not None:
        return Path(explicit)
    env_value = os.environ.get(ENV_CONFIG_VAR)
    if env_value:
        return Path(env_value)
    return None


def load_config(path: Path | None = None) -> ProjectConfig:
    """Load and validate a configuration.

    With no path (and no environment variable), the built-in defaults are
    returned — the pipeline always has a valid configuration to run with.
    """
    resolved = resolve_config_path(path)
    if resolved is None:
        return ProjectConfig()
    if not resolved.exists():
        raise FileNotFoundError(f"Config file not found: {resolved}")
    with resolved.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config file must contain a mapping at the top level: {resolved}")
    return ProjectConfig.model_validate(raw)

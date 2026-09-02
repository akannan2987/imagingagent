"""Typed configuration: what a run should do.

Why typed? A YAML file is just text; a typo like ``review_budget_fraction: 10``
(meaning 10 %) would silently flag every case. Pydantic turns the text into
Python objects and checks each value against its declared type and range,
so mistakes fail loudly at load time instead of quietly at 2 a.m.

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


class DatasetConfig(BaseModel):
    """Which dataset to use and how to stand in for it when absent."""

    model_config = ConfigDict(extra="forbid")

    name: str = "msd_task04_hippocampus"
    modality: str = "MRI"
    source_url: str = "http://medicaldecathlon.com/"
    licence: str = "CC-BY-SA 4.0"
    use_synthetic_fallback: bool = True
    synthetic_cases: int = Field(default=20, ge=1, le=10_000)
    seed: int = Field(default=20260901, ge=0)


class AuditConfig(BaseModel):
    """The decision the audit serves: review budget and plausibility bounds."""

    model_config = ConfigDict(extra="forbid")

    review_budget_fraction: float = Field(default=0.10, ge=0.0, le=1.0)
    min_volume_mm3: float = Field(default=1000.0, gt=0)
    max_volume_mm3: float = Field(default=6000.0, gt=0)


class StorageConfig(BaseModel):
    """Which storage backend to use. Only ``local`` exists today."""

    model_config = ConfigDict(extra="forbid")

    backend: Literal["local"] = "local"
    base_dir: Path = Path(".")


class ProjectConfig(BaseModel):
    """The complete, validated configuration for one run."""

    model_config = ConfigDict(extra="forbid")

    project_name: str = "imagingagent"
    paths: PathsConfig = Field(default_factory=PathsConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

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

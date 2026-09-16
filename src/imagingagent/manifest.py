"""The case manifest: the list of cases a track will work on.

A manifest is the pipeline's shopping list. Ingestion writes it once; every
later stage (preprocess, segment, audit) reads it instead of scanning
folders again. It is the same shape for both tracks — a list of
``CaseRecord`` — so the shared layers never care which kind of image they
are looking at.

Stored as one JSON file per track under ``data/processed/`` through the
storage interface, so it moves to object storage without changes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .schemas import CaseRecord, Track
from .storage import Storage
from .utils import utc_now_iso


class Manifest(BaseModel):
    """Every case the track knows about, plus where they came from."""

    model_config = ConfigDict(extra="forbid")

    track: Track
    dataset: str = Field(description="Dataset name, e.g. 'msd_task04_hippocampus' or 'synthetic'.")
    created_at: str = Field(default_factory=utc_now_iso)
    synthetic: bool = Field(default=False, description="True when every case is generated.")
    run_id: str = Field(default="", description="The ingestion run that produced this manifest.")
    cases: list[CaseRecord] = Field(default_factory=list)

    @property
    def case_ids(self) -> list[str]:
        return [c.case_id for c in self.cases]

    def with_labels(self) -> list[CaseRecord]:
        """Cases that come with a reference label map (needed for training and scoring)."""
        return [c for c in self.cases if c.label_key is not None]

    def __len__(self) -> int:
        return len(self.cases)


def manifest_key(track: Track | str, processed_dir: str = "data/processed") -> str:
    """Storage key of a track's manifest, e.g. ``data/processed/manifest_mri.json``."""
    name = track.value if isinstance(track, Track) else str(track)
    return f"{processed_dir.rstrip('/')}/manifest_{name}.json"


def save_manifest(
    storage: Storage, manifest: Manifest, processed_dir: str = "data/processed"
) -> str:
    key = manifest_key(manifest.track, processed_dir)
    storage.write_text(key, manifest.model_dump_json(indent=2) + "\n")
    return key


def load_manifest(
    storage: Storage, track: Track | str, processed_dir: str = "data/processed"
) -> Manifest:
    key = manifest_key(track, processed_dir)
    if not storage.exists(key):
        raise FileNotFoundError(f"No manifest at {key}. Run: imagingagent ingest --track {track}")
    return Manifest.model_validate_json(storage.read_text(key))

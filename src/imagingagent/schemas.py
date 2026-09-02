"""Data contracts: the shapes every layer agrees on.

Think of these as customs forms. A case, a finding, a report — each must be
filled in correctly before it can cross from one layer to the next, and the
same forms are what a future HTTP or MCP server hands to callers. Because
they are Pydantic models they validate themselves, serialise to JSON, and can
publish their own JSON Schema (``AuditReport.model_json_schema()``), which is
exactly what agent tooling needs to know how to call us.

Only the contracts needed today are defined. Each later phase extends them
in place rather than inventing parallel shapes.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Modality(StrEnum):
    """Imaging modality. More are added as the modality registry grows."""

    MRI = "MRI"
    CT = "CT"
    SYNTHETIC = "SYNTHETIC"


class CaseRecord(BaseModel):
    """One subject/scan as the pipeline sees it."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(description="Stable identifier, e.g. 'hippocampus_001'.")
    image_key: str = Field(description="Storage key of the image volume (NIfTI).")
    label_key: str | None = Field(
        default=None, description="Storage key of a reference label map, if any."
    )
    modality: Modality = Modality.MRI
    spacing_mm: tuple[float, float, float] | None = Field(
        default=None, description="Voxel size in millimetres along each axis."
    )
    shape: tuple[int, int, int] | None = Field(default=None, description="Voxels along each axis.")
    synthetic: bool = Field(default=False, description="True when generated, not acquired.")
    source: str = Field(default="", description="Where the case came from (dataset name, URL).")


class Verdict(StrEnum):
    """The audit's decision for one case."""

    ACCEPT = "accept"  # trustworthy enough to use unreviewed
    REVIEW = "review"  # send to a human within the review budget
    REJECT = "reject"  # implausible; do not use


class Finding(BaseModel):
    """One measured fact about a segmentation and whether it passed."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Short machine name, e.g. 'volume_mm3'.")
    value: float | None = Field(default=None, description="Measured value; None if not computable.")
    unit: str = Field(default="", description="Unit of the value, e.g. 'mm3', 'dice'.")
    passed: bool | None = Field(
        default=None, description="Whether the check passed; None if informational."
    )
    message: str = Field(default="", description="Plain-language explanation.")


class AuditReport(BaseModel):
    """The audit result for one case: findings, a score and a verdict."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    case_id: str
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
    status: str = "started"
    finished_at: str | None = None
    notes: str = ""
    output_dir: Path | None = None

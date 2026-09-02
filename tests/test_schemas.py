"""Data contracts: they validate, serialise and publish a schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from imagingagent.schemas import AuditReport, CaseRecord, Finding, Modality, Verdict


def test_case_record_round_trip() -> None:
    case = CaseRecord(case_id="c001", image_key="data/raw/c001.nii.gz", spacing_mm=(1.0, 1.0, 1.0))
    again = CaseRecord.model_validate_json(case.model_dump_json())
    assert again == case
    assert again.modality is Modality.MRI


def test_audit_report_failed_findings_and_schema() -> None:
    report = AuditReport(
        run_id="r1",
        case_id="c001",
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


def test_score_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AuditReport(run_id="r", case_id="c", score=1.5)

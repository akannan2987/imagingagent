"""Run ledger: append-only history with a start line and a finish line."""

from __future__ import annotations

from imagingagent import __version__
from imagingagent.config import ProjectConfig
from imagingagent.ledger import RunLedger
from imagingagent.schemas import Track
from imagingagent.storage import LocalStorage


def test_start_and_finish_write_two_lines(storage: LocalStorage, config: ProjectConfig) -> None:
    ledger = RunLedger(storage)
    record = ledger.start("audit", config, notes="first", track="mri")
    assert record.status == "started"
    assert record.track is Track.MRI
    assert record.package_version == __version__
    assert record.config_hash == config.content_hash()

    closed = ledger.finish(record, status="finished")
    lines = storage.read_text(ledger.key).splitlines()
    assert len(lines) == 2
    assert closed.finished_at is not None

    latest = ledger.latest_per_run()
    assert latest[record.run_id].status == "finished"


def test_empty_ledger_reads_as_empty(storage: LocalStorage) -> None:
    assert RunLedger(storage).read_all() == []


def test_default_track_is_shared(storage: LocalStorage, config: ProjectConfig) -> None:
    record = RunLedger(storage).start("init", config)
    assert record.track is Track.SHARED

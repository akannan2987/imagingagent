"""The run ledger: an append-only history of every run.

Why append-only? Because a history you can edit is not a history. Each run
adds one JSON line to ``runs/ledger.jsonl`` and never modifies earlier
lines. The line records the configuration fingerprint, the package version
and the machine, so any result can be traced back to exactly what produced
it — the habit regulated analytics calls provenance.

JSONL ("JSON Lines") is one JSON object per line: trivial to append to,
trivial to read with any tool, and it never becomes an invalid file
half-way through a write.
"""

from __future__ import annotations

from . import __version__
from .config import ProjectConfig
from .schemas import RunRecord, Track
from .storage import Storage
from .utils import platform_summary, short_id, utc_now_iso

LEDGER_KEY = "runs/ledger.jsonl"


class RunLedger:
    def __init__(self, storage: Storage, key: str = LEDGER_KEY) -> None:
        self.storage = storage
        self.key = key

    def start(
        self,
        command: str,
        config: ProjectConfig,
        notes: str = "",
        track: Track | str = Track.SHARED,
    ) -> RunRecord:
        """Create a run record, write its 'started' line, and return it.

        ``track`` records which modality family the run served, so the
        ledger can be filtered per track (``imagingagent ledger list --track mri``).
        """
        record = RunRecord(
            run_id=short_id(),
            started_at=utc_now_iso(),
            command=command,
            config_hash=config.content_hash(),
            package_version=__version__,
            platform=platform_summary(),
            track=Track(track),
            notes=notes,
        )
        self._append(record)
        return record

    def finish(
        self, record: RunRecord, status: str = "finished", notes: str | None = None
    ) -> RunRecord:
        """Write the closing line for a run. The opening line stays untouched."""
        closed = record.model_copy(
            update={
                "status": status,
                "finished_at": utc_now_iso(),
                "notes": record.notes if notes is None else notes,
            }
        )
        self._append(closed)
        return closed

    def read_all(self) -> list[RunRecord]:
        """Every line in the ledger, oldest first."""
        if not self.storage.exists(self.key):
            return []
        lines = self.storage.read_text(self.key).splitlines()
        return [RunRecord.model_validate_json(line) for line in lines if line.strip()]

    def latest_per_run(self) -> dict[str, RunRecord]:
        """The last-written line for each run id (i.e. its final status)."""
        latest: dict[str, RunRecord] = {}
        for record in self.read_all():
            latest[record.run_id] = record
        return latest

    def _append(self, record: RunRecord) -> None:
        self.storage.append_text(self.key, record.model_dump_json() + "\n")

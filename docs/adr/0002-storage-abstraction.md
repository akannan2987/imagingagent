# ADR 0002 — All file access goes through a storage interface

**Status:** accepted · **Date:** 2026-09-01

## Context

Today everything is on one laptop. A real deployment keeps whole-slide
images (1–10 GB each) in cloud object storage and runs on machines that
do not share a disk. Code that calls `open()` on paths everywhere cannot
move.

## Decision

A `Storage` interface with six operations (`write_bytes`, `read_bytes`,
`exists`, `delete`, `list_keys`, `local_path`) and one backend
(`LocalStorage`). Keys are forward-slash strings on every operating
system; the backend maps them with `pathlib`. Keys are validated so the
storage root cannot be escaped. No module outside `storage.py` touches
the disk directly.

## Alternatives considered

- **Plain paths everywhere.** Rejected: every module would need rewriting
  to move to object storage.
- **Adopt a cloud SDK now (fsspec, boto3).** Rejected: adds dependencies
  and concepts to a project that fits on a laptop; the interface is what
  matters and it is small enough to own.

## Consequences

- Adding an S3-compatible backend is one class, no pipeline changes.
- `local_path` exists because image libraries want a path; a remote
  backend would download to a cache and return that path.
- The run ledger writes through the same interface (with `newline=""`
  so the file is byte-identical on Windows and elsewhere — a bug the
  three-OS CI caught).

# ADR 0003 — Every run is driven by a typed, hashed configuration

**Status:** accepted · **Date:** 2026-09-01

## Context

A run is only reproducible if its settings are written down. A settings
file that is plain text can carry silent mistakes (`review_budget_fraction:
10`). And "which settings produced this result?" must always have an
answer.

## Decision

All settings live in `configs/default.yaml`, validated on load by
pydantic models in `config.py` (types, ranges, unknown keys rejected).
Precedence: `--config` → `IMAGINGAGENT_CONFIG` → built-in defaults.
`ProjectConfig.content_hash()` fingerprints the configuration and the run
ledger records it with every run. A test asserts the YAML file and the
code defaults never drift apart.

## Alternatives considered

- **Command-line flags for everything.** Rejected: not versionable, not
  reviewable, easy to mistype.
- **Untyped dictionaries from YAML.** Rejected: mistakes surface at 2 a.m.
  inside a computation rather than at load time.

## Consequences

- Numbers that could change are never hard-coded; contributing rules
  enforce it.
- Phase 0c extends the model with a `tracks:` block without changing the
  loading or hashing.

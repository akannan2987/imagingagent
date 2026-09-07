# ADR 0007 — A lock file for the core, per-track requirement files for the rest

**Status:** accepted · **Date:** 2026-09-06

## Context

`requirements.txt` pins the four libraries the core asks for directly, but
each pulls in others (pydantic → pydantic-core, typer → click, rich …) whose
versions were whatever pip resolved on the day. Two machines a year apart
could install different trees. The imaging phases will add PyTorch, whose
CPU build comes from a separate package index and differs per platform;
and the project must stay installable in seconds for readers who only
want the core.

## Decision

1. **`requirements.lock`** — the complete frozen tree of the core plus the
   development tools, generated with
   `python -m pip freeze --exclude-editable > requirements.lock` in a clean
   virtual environment on the reference machine. Continuous integration
   installs from it on Windows, macOS and Linux, which is what proves it is
   portable. Any change to `requirements*.txt` regenerates it in the same
   commit.
2. **Per-track requirement files** — `requirements-mri.txt`,
   `requirements-pathology.txt`, `requirements-serve.txt`, added by the
   phase that first needs them, pinned, and pointing at the CPU build of
   PyTorch. `pyproject.toml` declares matching *extras* with ranges only, so
   `pip install -e ".[mri]"` works but the files are the verified path.
3. **No R environment.** The platform is Python end to end; the single R
   snippet in a tutorial is illustrative. If a real R component is ever
   added, it gets `renv.lock` and a new record.

## Alternatives considered

- **One lock for everything.** Rejected: PyTorch's platform-specific wheels
  make a single frozen file unportable, and the core would take minutes
  to install for readers who never touch imaging.
- **pip-tools / uv now.** `uv` produces a genuinely cross-platform lock and
  is the likely upgrade once per-track locks become awkward; adopting it
  today adds a tool to the setup guides before it is needed. Trigger: the
  first time a per-track lock needs platform markers to stay correct.

## Consequences

- CI reads `requirements.lock`; a pin change that breaks one operating
  system is visible before merge.
- Each track's tutorial begins with "install this track's requirements
  file" and `imagingagent doctor --track <name>` confirms it.

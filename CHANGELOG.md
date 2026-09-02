# Changelog

All notable changes to ImagingAgent are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`, where a
`0.x` version means the interfaces may still change between minor releases.

## [Unreleased]

### Added — Phase 0a: repository skeleton
- Installable `src/` package with a versioned `imagingagent` command line.
- Typed configuration (`configs/default.yaml` ↔ `imagingagent.config`) with
  validation, environment-variable override and a content hash.
- Storage abstraction with a local-disk backend and a path-traversal guard.
- Data contracts (`CaseRecord`, `Finding`, `AuditReport`, `RunRecord`) that
  validate, serialise and publish JSON Schema.
- Append-only run ledger (`runs/ledger.jsonl`) recording config hash,
  package version and platform for every run.
- Commands: `version`, `doctor`, `init`, `config show`, `ledger list`.
- 31 automated tests; lint and format checks with ruff.
- Continuous integration on Windows, macOS and Linux runners.

### Planned for 0.1.0
- Phase 0b: full documentation set (README, glossary, per-OS setup,
  architecture, git workflow, phase tutorials, roadmaps, contributing guide).
- Phase 1: ingestion — real MRI volumes (Medical Segmentation Decathlon,
  hippocampus task) with a synthetic fallback generator; NIfTI and DICOM
  readers preserving geometry metadata; the case manifest.

[Unreleased]: https://github.com/akannan2987/imagingagent/compare/master...develop

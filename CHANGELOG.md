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

### Added — Phase 0b: documentation set for the two-track platform
- `README.md`: two tracks (MRI volumes, digital pathology), one shared
  audit layer; honest phase-by-phase status; data at a glance; honesty notes.
- `docs/HANDBOOK.md`: the single live guide from day 0 to the finished
  product, with stages, checkpoints and commit messages.
- `docs/00-glossary.md` (both modalities), `docs/02-architecture.md`,
  `docs/05-roadmap.md`, `docs/06-product-and-technology-roadmap.md`,
  `docs/08-data-and-models.md`, `docs/TOOL_COOKBOOK.md`, `docs/UNINSTALL.md`,
  six architecture decision records under `docs/adr/`.
- Illustrations in `docs/img/`: cover, architecture, geometry (voxel vs
  pixel), review-budget funnel.
- Setup guides gain a "track extras" step; `CONTRIBUTING.md` gains the
  symmetry, handbook and ADR rules.

### Changed
- Ruff no longer format-checks Markdown snippets or the git-ignored
  `private/` folder.
- `LocalStorage.append_text` writes with `newline=""` so the run ledger is
  byte-identical on Windows (caught by CI).
- CI actions bumped to `checkout@v5` / `setup-python@v6`.

### Planned for 0.1.0 (end of Phase 3)
- Phase 0c: two-track refactor — track configuration, `VolumeGeometry` and
  `TileGeometry` contracts, modality registry, `--track` on every command.
- Phase 1: ingestion for both tracks with public datasets and synthetic
  generators.
- Phase 2: preprocessing for both tracks.
- Phase 3: segmentation for both tracks — classical, learned, imported.

[Unreleased]: https://github.com/akannan2987/imagingagent/compare/master...develop

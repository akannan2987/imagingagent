# ADR 0001 — One platform, two tracks, one shared spine

**Status:** accepted · **Date:** 2026-09-06

## Context

The platform must handle two very different image families — volumetric
scans (MRI, later CT) and microscopy slides (H&E, IHC, multiplex IF,
spatial transcriptomics). They differ in geometry, file formats, models
and downstream analyses. The obvious options were two repositories, or
one repository with the modality as a first-class concept.

## Decision

One repository, one installable package, two **tracks** (`mri`,
`pathology`) sharing a foundation (config, storage, contracts, ledger,
CLI) and a shared analysis layer (audit and triage, benchmark harness,
report writer, serving). Every capability phase delivers for both tracks
in the same phase with the same command shape (`--track`); modality-
specific phases belong to one track and say so (the **symmetry rule**).

## Alternatives considered

- **Two repositories.** Rejected: the audit layer — the project's central
  idea — would be maintained twice and drift twice; the "same question,
  two data types" argument would be lost.
- **One track first, the second bolted on later.** Rejected: contracts
  designed for one modality bake in its assumptions (e.g. `spacing_mm`
  everywhere); retrofitting is more expensive than designing the geometry
  union now.

## Consequences

- Contracts carry a `track` and a geometry union (`VolumeGeometry |
  TileGeometry`), decided in Phase 0c.
- The plan may not let one track fall behind; a lagging track is a bug in
  the plan.
- Optional dependencies are split per track so the core installs in
  seconds.

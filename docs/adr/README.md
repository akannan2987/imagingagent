[← README](../../README.md) · [Handbook](../HANDBOOK.md) · [Architecture](../02-architecture.md)

# Architecture decision records

An **architecture decision record (ADR)** is a one-page note that captures
one design decision: the situation, the options, the choice, and what it
commits us to. *Analogy:* the minutes of a meeting where a choice was
made, so that nobody has to re-argue it a year later — and so that a
newcomer can see *why* the code is shaped the way it is, not only *how*.

Each record has the same sections: **Status**, **Date**, **Context**,
**Decision**, **Alternatives considered**, **Consequences**. Records are
never edited after acceptance; a change of mind is a new record that
supersedes the old one.

| # | Decision | Status |
|---|---|---|
| [0001](0001-two-tracks-one-platform.md) | One platform with two modality tracks and a shared spine, rather than two projects | accepted |
| [0002](0002-storage-abstraction.md) | All file access goes through a storage interface | accepted |
| [0003](0003-config-driven-typed-runs.md) | Every run is driven by a typed, hashed configuration | accepted |
| [0004](0004-cpu-first.md) | CPU-first design with a documented GPU path | accepted |
| [0005](0005-instanseg-for-nuclei.md) | InstanSeg as the pre-trained nucleus/cell model | accepted |
| [0006](0006-phikon-as-default-foundation-model.md) | Phikon (ViT-B) as the default pathology foundation model | accepted |

New records are added by the phase that makes the decision and listed in
the phase's tutorial.

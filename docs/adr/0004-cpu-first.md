# ADR 0004 — CPU-first design with a documented GPU path

**Status:** accepted · **Date:** 2026-09-06

## Context

The platform must run on a standard laptop (including Intel Macs with no
GPU acceleration) and on RHEL 8 VMs. Most imaging tutorials assume a GPU,
which excludes most readers and makes results unreproducible for them.

## Decision

Every phase runs end to end on CPU within a stated budget. Datasets and
models are chosen for that: small hippocampus volumes; tile datasets; a
ViT-B foundation model rather than a ViT-g; a pre-trained nucleus model
that runs in seconds per tile. A `--device` switch and a free-GPU notebook
path are documented for anyone wanting larger models; gated or GPU-sized
models are roadmap items with a trigger.

## Alternatives considered

- **GPU-required.** Rejected: excludes the target reader and half the
  target machines.
- **Cloud-only.** Rejected: cost, accounts, and the loss of "clone and run".

## Consequences

- Some results are deliberately modest (small models, subsets) and say so.
- Phase budgets are stated in wall-clock minutes and measured.

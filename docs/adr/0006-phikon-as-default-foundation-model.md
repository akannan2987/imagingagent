# ADR 0006 — Phikon (ViT-B) as the default pathology foundation model

**Status:** accepted · **Date:** 2026-09-04

## Context

The foundation-model benchmark needs at least one pathology-specific
pre-trained encoder that a reader can download without an access
request and run on CPU. Most strong models (UNI, CONCH, Virchow,
Prov-GigaPath, OpenMidnight, H-optimus-0) are gated, over 1 GB, or both.

## Decision

Phikon (Owkin, ViT-B, ≈ 340 MB, self-supervised on 40 M TCGA tiles) as
the default: ungated, CPU-practical, well documented. Phikon-v2 (ViT-L,
1.2 GB) is a documented config switch. Hibou-B (Apache-2.0 but behind a
click-through gate requiring a free account) is optional. The benchmark
always includes general-domain baselines (DINOv2-small, ImageNet
ResNet-50) and a vision-language model (PLIP) for zero-shot.

## Alternatives considered

- **A gated model as default.** Rejected: "clone and run" would fail for
  most readers.
- **No pathology FM, only general baselines.** Rejected: the field's
  central claim would go untested.

## Consequences

- Phikon's non-commercial licence is inherited by results derived from it
  and stated in the benchmark report.
- The embedding contract accepts any Hugging Face encoder, so gated
  models slot in when access is granted.

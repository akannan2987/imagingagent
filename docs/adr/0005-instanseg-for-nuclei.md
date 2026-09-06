# ADR 0005 — InstanSeg as the pre-trained nucleus/cell model

**Status:** accepted · **Date:** 2026-09-04

## Context

The pathology track needs a pre-trained instance-segmentation model for
nuclei and cells that runs on CPU on all three operating systems and
handles both brightfield (H&E, IHC) and multi-channel fluorescence. The
options were StarDist, Cellpose, HoVer-Net/CellViT and InstanSeg.

## Decision

InstanSeg (`instanseg-torch`): pure PyTorch/TorchScript, models of a few
megabytes, `brightfield_nuclei` for H&E and DAB and
`fluorescence_nuclei_and_cells` which is channel-invariant — one library
covers every stain in the track without retraining. It is also the model
family QuPath ships.

## Alternatives considered

- **StarDist.** Needs TensorFlow, which no longer supports Intel Macs.
- **Cellpose 4.** SAM-based and heavy on CPU; earlier small models are
  possible but the install pins fight the rest of the stack.
- **HoVer-Net / CellViT.** Larger weights, some non-commercial terms;
  noted in the roadmap as alternatives the contract already accepts.

## Consequences

- Fluorescence segmentation on MCMICRO and DeepLIIF uses the same call.
- The classical baseline remains mandatory, and imported masks from any
  tool go through the same contract.

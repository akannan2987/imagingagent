[← README](../README.md) · [Handbook](HANDBOOK.md) · [Product roadmap](06-product-and-technology-roadmap.md) · [Glossary](00-glossary.md)

# 05 — Roadmap: what this repository builds next

**Prerequisites:** [`02-architecture.md`](02-architecture.md).
**Learning goal:** know exactly what is built, what comes next in which
order, why the order is what it is, and what would change a deferred item
into a scheduled one.

This document is about *this repository*. The finished *product* — web
front end, cloud, integrations, commercial questions — is in
[`06-product-and-technology-roadmap.md`](06-product-and-technology-roadmap.md).
Progress is also mirrored in the [Handbook](HANDBOOK.md) and in the README's
*Results, phase by phase* table.

## How to read status

| Mark | Meaning |
|---|---|
| ✅ | built, tested, on `master` |
| 🔧 | in progress on `develop` |
| ⏳ | scheduled, not started |
| 🔒 | deferred; the trigger that schedules it is stated |

Every phase delivers for both tracks unless marked track-specific. CPU
budget is wall-clock on an Intel laptop without a GPU, excluding downloads.

## The phase plan

| # | Phase | mri | pathology | shared | CPU | Status | Tag |
|---|---|---|---|---|---|---|---|
| 0 | Skeleton | — | — | config, storage, contracts, ledger, CLI, tests, 3-OS CI | < 1 min | ✅ | — |
| 0b | Documentation set | — | — | README, handbook, glossary, architecture, roadmaps, data doc, cookbook, uninstall, ADRs | 0 | 🔧 | — |
| 0c | Two-track refactor | track config, `VolumeGeometry` | track config, `TileGeometry` | `--track` on every command, `doctor` per track, modality registry, tests updated in place | < 1 min | ⏳ | — |
| 1 | Ingestion | MSD hippocampus download + synthetic volumes; NIfTI + DICOM readers | Kather-2016, PanNuke fold, DeepLIIF test set, MCMICRO exemplar-001, Visium sample; synthetic H&E / mIF / spot generators; OME-TIFF and SVS readers | case manifest; checksums; every command runs offline | < 5 min | ⏳ | — |
| 2 | Preprocessing | resample, normalise, denoise, rigid register, paired transforms | colour deconvolution, Macenko, stain augmentation, tissue mask, tiling | augmentation as robustness tool | < 5 min | ⏳ | — |
| 3 | Segmentation | classical; 3D U-Net (≈ 10–15 min training); Dice / HD95 / NSD; import label maps | classical; InstanSeg; Dice / AJI / PQ; import label maps and QuPath GeoJSON | one segmentation contract; per-case failure lists | ≈ 20 min | ⏳ | **v0.1.0** |
| 4 | Uncertainty & repeatability *(mri)* | TTA, MC-dropout, calibration; perturbation study → minimum detectable difference | — | — | ≈ 15 min | ⏳ | — |
| 5 | Features & biomarkers | volume, shape, CIs | morphology, intensity, texture; nucleus-type classifier; IHC/mIF positivity; density and composition, CIs | one tabular biomarker contract | < 5 min | ⏳ | — |
| 6 | Foundation-model benchmark *(pathology)* | — | Phikon vs DINOv2-small vs ResNet-50 vs PLIP zero-shot; linear probe + k-NN on a documented 1,600-tile subset (full 5,000 optional); stain-shift robustness; calibration | embedding contract | ≈ 15 min | ⏳ | — |
| 7 | Spatial & graph learning *(pathology)* | — | k-NN / Delaunay cell graphs; neighbourhood enrichment, co-occurrence, distances; small GNN vs feature-aggregation baseline | — | ≈ 10 min | ⏳ | — |
| 8 | Multi-modal | biomarkers ⨝ simulated covariates: stratification, endpoint sensitivity | H&E embeddings → Visium expression clusters; IHC ↔ registered mIF positivity agreement | join contract | ≈ 10 min | ⏳ | **v0.2.0** |
| 9 | Audit & triage | uncertainty + shape + registration features | blur, folds, pen, stain outlier, OOD, implausible cell statistics | one audit module, calibrated score, review queue, review budget | < 5 min | ⏳ | — |
| 10 | Benchmark & report | `benchmark --track mri` | `--track pathology` | ledger-traced tables and figures; `07-benchmark-report.md`; `09-talk-outline.md` | ≈ 15 min | ⏳ | — |
| 11 | Serving | slices in the review UI | tiles and overlays in the review UI | grounded report writer; MCP server (read-only tools); Streamlit review queue | seconds | ⏳ | — |
| 12 | Release | — | — | Dockerfile (Podman-compatible), free-GPU notebook path, HPC note, CHANGELOG | build ≈ 10 min | ⏳ | **v0.3.0** |

**Why this order.** Capability by capability, both tracks at once, so the
platform is usable end to end early (v0.1.0 after segmentation) and the
shared audit layer (Phase 9) has real signals from both tracks to learn
from. The modality-specific phases (4, 6, 7) sit between segmentation and
audit because the audit consumes their outputs.

## Deferred items and their triggers

Symmetric by design: each track lists the same categories.

### mri track

| Item | Status | Trigger / approach |
|---|---|---|
| CT via MSD Spleen | 🔒 | a config switch documented in Phase 1; larger volumes, so the free-GPU notebook path is recommended; scheduled when a second modality is needed for a demo |
| PET, DXA, ultrasound, ophthalmic imaging | 🔒 | the modality registry (Phase 0c) makes each a plug-in with its own geometry and reader; scheduled when a public dataset under 2 GB with a permissive licence is identified for it |
| Deformable registration (ANTs / SimpleITK BSpline) | 🔒 | when a longitudinal (same patient, two dates) dataset is added |
| Larger 3D models (nnU-Net, SegResNet, UNETR) | 🔒 | GPU trigger: documented free-GPU notebook path; the segmentation contract already accepts any model |
| Multi-class segmentation (both hippocampi, subfields) | 🔒 | MSD Task04 labels two subregions — the first extension after v0.1.0 |
| Vendor-specific formats, PACS integration | 🔒 | product roadmap |
| 3D Slicer extension | 🔒 | overlays already export as NIfTI; an extension when a user asks for one |

### pathology track

| Item | Status | Trigger / approach |
|---|---|---|
| Gated foundation models (UNI, CONCH, Virchow, Prov-GigaPath, OpenMidnight, H-optimus-0) | 🔒 | the embedding contract accepts any encoder; add when access is granted and the free-GPU path is used (sizes > 2 GB) |
| Hibou-B (Apache-2.0, click-gate) | 🔒 | optional in Phase 6 for anyone with a free account; not required |
| Larger datasets (BCI HER2 pairs ≈ 4 GB, Lizard, CoNSeP, NCT-CRC-100K 12 GB, TCGA slides) | 🔒 | disk-budget trigger (project stays under 6 GB); download scripts stay generic |
| Whole-slide inference (full WSI, not tiles) | 🔒 | the tiler is WSI-ready via openslide-bin / tiffslide; scheduled with the first real slide; object storage recommended |
| Virtual staining (IHC → mIF, H&E → IHC) and image synthesis | 🔒 | GPU trigger; DeepLIIF pairs are already ingested for training data; roadmap for generative models |
| CellViT / HoVer-Net as alternative nucleus models | 🔒 | licence and size review; contract already accepts them |
| 10x Xenium / CosMx (single-cell spatial transcriptomics) | 🔒 | when a small public sample under 2 GB is identified |
| QuPath extension, Napari plugin, OMERO connector | 🔒 | outputs already export as QuPath-readable GeoJSON; plugins when a user asks |
| Vendor formats (NDPI, MRXS) | 🔒 | openslide-bin already supports them; a test slide when one is available |

### shared

| Item | Status | Trigger / approach |
|---|---|---|
| Language-model backend for the report writer | ⏳ Phase 11 | template backend ships by default; an HTTP backend is configured by environment variable and never sees images |
| Retrieval over past reports and literature | 🔒 | needs a corpus of reports first |
| Knowledge graph and ontologies (SNOMED CT, RadLex, Cell Ontology, UBERON) | 🔒 | findings are already structured; coding them is product roadmap |
| Object storage backend | 🔒 | first real slide cohort; the interface exists |
| Orchestrator (Airflow / Dagster / Prefect) | 🔒 | scheduled batch audits; product roadmap |
| PostgreSQL for findings and ledger | 🔒 | multi-user; product roadmap |
| Data / model versioning (DVC) | 🔒 | more than one trained model in circulation |
| MCP client (ImagingAgent calling other servers) | 🔒 | a second server worth calling (PACS, literature) |
| Kubernetes / serverless, monitoring, cost model | 🔒 | hosted deployment; product roadmap |

## Publications and talks

The benchmark report (`07-benchmark-report.md`) is written in the
structure of a methods paper — problem, data, methods, results,
limitations, reproducibility — and the talk outline (`09-talk-outline.md`)
in the structure of a 15-minute conference talk. Both arrive in Phase 10,
built from ledger-traced numbers. Submitting them anywhere is a decision
for after v0.3.0.

## How this document is maintained

At the end of every phase: flip the status mark, fill the CPU figure with
the measured one, add the phase's link, and move any item whose trigger
fired from 🔒 to ⏳. The same three edits go into the [Handbook](HANDBOOK.md)
and the README table. Roadmap and reality are not allowed to drift.

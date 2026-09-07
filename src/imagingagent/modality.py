"""The modality registry: every kind of image the platform knows about.

A registry is a lookup table. Each entry says which track a modality
belongs to, which geometry it uses, how its files usually end, and whether
it is implemented or planned. Keeping planned modalities *in the code* (not
only in a roadmap document) means ``imagingagent modalities`` always shows
the honest picture, and adding one later is a one-line entry plus a reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .schemas import Modality, Track

GeometryKind = Literal["volume", "tile"]
Status = Literal["implemented", "planned"]


@dataclass(frozen=True)
class ModalitySpec:
    name: str
    track: Track
    geometry: GeometryKind
    description: str
    status: Status
    extensions: tuple[str, ...] = ()
    modality: Modality | None = None  # None for planned modalities without an enum member


_SPECS: tuple[ModalitySpec, ...] = (
    ModalitySpec(
        "MRI",
        Track.MRI,
        "volume",
        "Magnetic resonance imaging — soft tissue in 3D",
        "implemented",
        (".nii", ".nii.gz", ".dcm"),
        Modality.MRI,
    ),
    ModalitySpec(
        "CT",
        Track.MRI,
        "volume",
        "Computed tomography — X-ray volumes; a config switch to MSD Spleen",
        "planned",
        (".nii", ".nii.gz", ".dcm"),
    ),
    ModalitySpec(
        "PET",
        Track.MRI,
        "volume",
        "Positron emission tomography — metabolic activity in 3D",
        "planned",
        (".nii", ".nii.gz", ".dcm"),
    ),
    ModalitySpec(
        "DXA",
        Track.MRI,
        "volume",
        "Dual-energy X-ray absorptiometry — bone density",
        "planned",
        (".dcm",),
    ),
    ModalitySpec(
        "ULTRASOUND",
        Track.MRI,
        "volume",
        "Ultrasound — sound-wave imaging, 2D/3D",
        "planned",
        (".dcm",),
    ),
    ModalitySpec(
        "OPHTHALMIC",
        Track.MRI,
        "volume",
        "Retinal imaging (fundus, OCT)",
        "planned",
        (".dcm", ".tif"),
    ),
    ModalitySpec(
        "HE",
        Track.PATHOLOGY,
        "tile",
        "Haematoxylin and eosin — the standard tissue stain",
        "implemented",
        (".tif", ".tiff", ".svs", ".png"),
        Modality.HE,
    ),
    ModalitySpec(
        "IHC",
        Track.PATHOLOGY,
        "tile",
        "Immunohistochemistry — one protein marked brown (DAB)",
        "implemented",
        (".tif", ".tiff", ".svs", ".png"),
        Modality.IHC,
    ),
    ModalitySpec(
        "MIF",
        Track.PATHOLOGY,
        "tile",
        "Multiplex immunofluorescence — many markers, one channel each",
        "implemented",
        (".ome.tif", ".ome.tiff", ".tif"),
        Modality.MIF,
    ),
    ModalitySpec(
        "SPATIAL_TRANSCRIPTOMICS",
        Track.PATHOLOGY,
        "tile",
        "Gene activity measured at spots over an H&E image (10x Visium)",
        "implemented",
        (".h5ad",),
        Modality.SPATIAL_TRANSCRIPTOMICS,
    ),
    ModalitySpec(
        "XENIUM",
        Track.PATHOLOGY,
        "tile",
        "Single-cell spatial transcriptomics (10x Xenium, CosMx)",
        "planned",
        (".h5ad", ".parquet"),
    ),
    ModalitySpec(
        "SYNTHETIC",
        Track.SHARED,
        "volume",
        "Generated stand-in data; geometry follows the track it imitates",
        "implemented",
        (),
        Modality.SYNTHETIC,
    ),
)

REGISTRY: dict[str, ModalitySpec] = {spec.name: spec for spec in _SPECS}


def spec_for(modality: Modality | str) -> ModalitySpec:
    """Look a modality up; unknown names fail loudly."""
    name = modality.value if isinstance(modality, Modality) else str(modality).upper()
    try:
        return REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown modality {name!r}; known: {sorted(REGISTRY)}") from exc


def specs_for_track(track: Track | str, *, include_planned: bool = True) -> list[ModalitySpec]:
    """Every modality belonging to a track, implemented first."""
    wanted = track if isinstance(track, Track) else Track(track)
    chosen = [s for s in _SPECS if s.track is wanted or s.track is Track.SHARED]
    if not include_planned:
        chosen = [s for s in chosen if s.status == "implemented"]
    return sorted(chosen, key=lambda s: (s.status != "implemented", s.name))


def implemented() -> list[ModalitySpec]:
    return [s for s in _SPECS if s.status == "implemented"]

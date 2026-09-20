"""Reading tiles and slides with their geometry.

A slide's geometry is the note that says how many microns one pixel covers,
which pyramid level the pixels came from, where the tile sits on the slide,
and which colour layers (channels) it has. Formats differ in where they keep
that note:

- plain TIFF / PNG tiles (Kather-2016, DeepLIIF): no note in the file; the
  dataset's documentation gives it, so the caller passes ``microns_per_pixel``
- OME-TIFF (MCMICRO): an XML block inside the file carries physical pixel
  size and channel names; ``markers.csv`` beside it carries the panel
- the PanNuke mirror: Parquet rows with PNG bytes; 0.25 µm/px by documentation
- Visium (``.h5ad``): spot coordinates and scale factors live in the file

Libraries are imported lazily so the core installs without them; a clear
message names the requirements file when one is missing.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import numpy as np

from ...schemas import TileGeometry

PATHOLOGY_REQUIREMENTS = "python -m pip install -r requirements-pathology.txt"


def _need(module: str):
    import importlib

    try:
        return importlib.import_module(module)
    except ImportError as exc:  # pragma: no cover - only without the extras
        raise ImportError(
            f"{module} is required for this reader. Run: {PATHOLOGY_REQUIREMENTS}"
        ) from exc


# ---------------------------------------------------------------------------
# Brightfield tiles: TIFF / PNG (Kather-2016, DeepLIIF panels, PanNuke tiles)
# ---------------------------------------------------------------------------


def read_rgb_tile(
    path: Path, microns_per_pixel: float, stain: str = "HE", magnification: float | None = None
) -> tuple[np.ndarray, TileGeometry]:
    """Load a small RGB tile → (H×W×3 uint8 array, geometry).

    The file carries no scale bar, so ``microns_per_pixel`` comes from the
    dataset's documentation (0.495 for Kather-2016, 0.25 for PanNuke).
    Grey or RGBA files are converted to RGB so every tile has three channels.
    """
    path = Path(path)
    if path.suffix.lower() in {".tif", ".tiff"}:
        tifffile = _need("tifffile")
        array = tifffile.imread(str(path))
    else:
        image_module = _need("PIL.Image")
        with image_module.open(path) as image:
            array = np.asarray(image.convert("RGB"))
    array = _to_rgb_uint8(array)
    height, width = array.shape[:2]
    geometry = TileGeometry(
        microns_per_pixel=microns_per_pixel,
        width=width,
        height=height,
        magnification=magnification,
        channels=["R", "G", "B"],
        stain=stain,
    )
    return array, geometry


def _to_rgb_uint8(array: np.ndarray) -> np.ndarray:
    if array.ndim == 2:
        array = np.stack([array] * 3, axis=-1)
    if array.shape[-1] == 4:
        array = array[..., :3]
    if array.dtype != np.uint8:
        top = float(array.max()) or 1.0
        array = (array.astype(float) / top * 255).round().astype(np.uint8)
    return np.ascontiguousarray(array)


def write_rgb_png(array: np.ndarray, path: Path) -> Path:
    """Save an H×W×3 uint8 array as PNG (used by the synthetic generators)."""
    image_module = _need("PIL.Image")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image_module.fromarray(np.asarray(array, dtype=np.uint8)).save(path)
    return path


# ---------------------------------------------------------------------------
# DeepLIIF: six 512×512 panels side by side in one PNG
# ---------------------------------------------------------------------------

DEEPLIIF_PANELS = ("IHC", "Hematoxylin", "DAPI", "Lap2", "Marker", "Seg")


def read_deepliif_composite(
    path: Path, microns_per_pixel: float = 0.25
) -> tuple[dict[str, np.ndarray], TileGeometry]:
    """Split a DeepLIIF composite image into its named panels.

    The dataset stores each case as one wide image: the IHC tile followed by
    its co-registered hematoxylin, DAPI, LAP2β and marker (Ki67) fluorescence
    channels and a segmentation mask, each ``height`` pixels wide. Returns a
    dict panel-name → H×W×3 array, plus the geometry of one panel.
    """
    image_module = _need("PIL.Image")
    with image_module.open(path) as image:
        array = np.asarray(image.convert("RGB"))
    height, width = array.shape[:2]
    n = width // height
    if n * height != width or n not in (5, 6):
        raise ValueError(
            f"{path}: expected 5 or 6 square panels side by side, got {width}×{height}"
        )
    names = DEEPLIIF_PANELS[:n]
    panels = {
        name: np.ascontiguousarray(array[:, i * height : (i + 1) * height])
        for i, name in enumerate(names)
    }
    geometry = TileGeometry(
        microns_per_pixel=microns_per_pixel,
        width=height,
        height=height,
        channels=list(names),
        stain="IHC+mIF",
    )
    return panels, geometry


# ---------------------------------------------------------------------------
# OME-TIFF multichannel (MCMICRO exemplar, any multiplex IF export)
# ---------------------------------------------------------------------------


def read_markers_csv(path: Path) -> list[str]:
    """Channel names from an MCMICRO-style ``markers.csv`` (column ``marker_name``)."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    key = (
        "marker_name"
        if rows and "marker_name" in rows[0]
        else (list(rows[0].keys())[0] if rows else None)
    )
    return [row[key].strip() for row in rows] if key else []


def read_ome_tiff(
    path: Path,
    series: int = 0,
    channel_names: list[str] | None = None,
    default_microns_per_pixel: float | None = None,
) -> tuple[np.ndarray, TileGeometry]:
    """Load one series of an OME-TIFF → (C×H×W array, geometry).

    Physical pixel size and channel names are taken from the OME-XML when
    present; otherwise ``channel_names`` and ``default_microns_per_pixel``
    fill in, and the geometry says so via the ``stain`` field.
    """
    tifffile = _need("tifffile")
    with tifffile.TiffFile(str(path)) as tif:
        if not tif.series:
            raise ValueError(f"{path}: no image series")
        data = tif.series[series].asarray()
        xml = tif.ome_metadata or ""
    data = np.asarray(data)
    if data.ndim == 2:
        data = data[None]
    if data.ndim != 3:
        raise ValueError(f"{path}: expected (C, H, W), got shape {data.shape}")
    mpp = _ome_physical_size_x(xml) or default_microns_per_pixel
    if mpp is None:
        raise ValueError(
            f"{path}: no PhysicalSizeX in OME metadata; pass default_microns_per_pixel"
        )
    names = _ome_channel_names(xml) or channel_names or [f"ch{i}" for i in range(data.shape[0])]
    names = list(names)[: data.shape[0]] + [f"ch{i}" for i in range(len(names), data.shape[0])]
    geometry = TileGeometry(
        microns_per_pixel=float(mpp),
        width=int(data.shape[2]),
        height=int(data.shape[1]),
        channels=names,
        stain="MIF",
    )
    return data, geometry


def _ome_physical_size_x(xml: str) -> float | None:
    match = re.search(r'PhysicalSizeX="([0-9.eE+-]+)"', xml)
    if not match:
        return None
    value = float(match.group(1))
    unit = re.search(r'PhysicalSizeXUnit="([^"]+)"', xml)
    if unit and unit.group(1) in ("nm",):
        value /= 1000.0
    if unit and unit.group(1) in ("mm",):
        value *= 1000.0
    return value


def _ome_channel_names(xml: str) -> list[str]:
    return [m for m in re.findall(r'<Channel[^>]*\bName="([^"]+)"', xml)]


def write_ome_tiff(data: np.ndarray, geometry: TileGeometry, path: Path) -> Path:
    """Save a C×H×W array as OME-TIFF with pixel size and channel names (synthetic mIF)."""
    tifffile = _need("tifffile")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "axes": "CYX",
        "PhysicalSizeX": geometry.microns_per_pixel,
        "PhysicalSizeXUnit": "µm",
        "PhysicalSizeY": geometry.microns_per_pixel,
        "PhysicalSizeYUnit": "µm",
        "Channel": {"Name": list(geometry.channels)},
    }
    tifffile.imwrite(str(path), np.asarray(data), metadata=metadata, ome=True)
    return path


# ---------------------------------------------------------------------------
# PanNuke tiles extracted from the Parquet mirror
# ---------------------------------------------------------------------------


def decode_png_bytes(blob: bytes) -> np.ndarray:
    image_module = _need("PIL.Image")
    with image_module.open(io.BytesIO(blob)) as image:
        return np.asarray(image)


def read_pannuke_tile(
    image_path: Path, label_path: Path
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load an extracted PanNuke tile → (H×W×3 image, H×W instance map, per-instance types).

    ``label_path`` is an ``.npz`` written by the download script with
    ``instances`` (uint16, 0 = background, k = nucleus k) and ``types``
    (int8, index i-1 = category of nucleus i; 0 Neoplastic, 1 Inflammatory,
    2 Connective, 3 Dead, 4 Epithelial).
    """
    image, _ = read_rgb_tile(image_path, microns_per_pixel=0.25, magnification=40.0)
    with np.load(label_path) as npz:
        instances = npz["instances"].astype(np.uint16)
        types = npz["types"].astype(np.int8)
    return image, instances, types


# ---------------------------------------------------------------------------
# Visium spatial transcriptomics (.h5ad)
# ---------------------------------------------------------------------------


def read_visium_h5ad(path: Path) -> tuple[object, np.ndarray, TileGeometry]:
    """Load a Visium AnnData → (adata, hires H&E image H×W×3, geometry of that image).

    The spot coordinates are in full-resolution pixels; the stored image is
    a downscaled "hires" copy with a scale factor in ``uns['spatial']``. The
    geometry describes the stored image; Visium spots are 55 µm across and
    100 µm apart, which pins the microns-per-pixel of the full image at
    roughly 0.5 µm for this sample — recorded honestly as an estimate.
    """
    anndata = _need("anndata")
    adata = anndata.read_h5ad(str(path))
    spatial = adata.uns.get("spatial", {})
    if not spatial:
        raise ValueError(f"{path}: no 'spatial' entry in uns — not a Visium AnnData")
    library = next(iter(spatial.values()))
    image = np.asarray(library["images"]["hires"])
    image = _to_rgb_uint8(image)
    scale = float(library["scalefactors"]["tissue_hires_scalef"])
    spot_diameter_fullres = float(library["scalefactors"]["spot_diameter_fullres"])
    fullres_mpp = 55.0 / spot_diameter_fullres  # a Visium spot is 55 µm across
    geometry = TileGeometry(
        microns_per_pixel=fullres_mpp / scale,
        width=int(image.shape[1]),
        height=int(image.shape[0]),
        channels=["R", "G", "B"],
        stain="HE",
    )
    return adata, image, geometry

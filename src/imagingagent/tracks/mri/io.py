"""Reading and writing volumes with their geometry.

A NIfTI file stores voxel values plus an *affine* — a 4×4 matrix that maps
voxel indices to millimetres in the scanner. Everything this module does
is: read the values, read the affine, and turn the affine into the
``VolumeGeometry`` contract (spacing, orientation, origin). A DICOM series
stores the same information across many single-slice files; SimpleITK
sorts and stacks them.

The two readers are imported lazily so the core package installs without
imaging libraries; a clear message says which file to install when one is
missing.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ...schemas import VolumeGeometry

MRI_REQUIREMENTS = "python -m pip install -r requirements-mri.txt"


def _nibabel():
    try:
        import nibabel as nib
    except ImportError as exc:  # pragma: no cover - exercised only without extras
        raise ImportError(f"nibabel is required for NIfTI files. Run: {MRI_REQUIREMENTS}") from exc
    return nib


def _sitk():
    try:
        import SimpleITK as sitk
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            f"SimpleITK is required for DICOM series. Run: {MRI_REQUIREMENTS}"
        ) from exc
    return sitk


def geometry_from_affine(affine: np.ndarray, shape: tuple[int, int, int]) -> VolumeGeometry:
    """Turn a NIfTI affine into the geometry contract.

    Spacing is the length of each of the affine's first three columns (how
    far one step along an axis moves in millimetres); orientation is the
    three-letter axis code nibabel derives from the same matrix; origin is
    the translation column.
    """
    nib = _nibabel()
    affine = np.asarray(affine, dtype=float)
    spacing = tuple(float(np.linalg.norm(affine[:3, i])) for i in range(3))
    orientation = "".join(nib.orientations.aff2axcodes(affine))
    origin = tuple(float(v) for v in affine[:3, 3])
    return VolumeGeometry(
        spacing_mm=spacing,
        shape=tuple(int(n) for n in shape),
        orientation=orientation,
        origin_mm=origin,
    )


def read_nifti(path: Path) -> tuple[np.ndarray, VolumeGeometry]:
    """Load a ``.nii`` / ``.nii.gz`` file → (array, geometry).

    Only the first three dimensions are kept; a fourth (time or channel)
    dimension is not expected in this track and raises.
    """
    nib = _nibabel()
    image = nib.load(str(path))
    data = np.asarray(image.dataobj)
    if data.ndim != 3:
        raise ValueError(f"{path}: expected a 3D volume, got shape {data.shape}")
    return data, geometry_from_affine(image.affine, data.shape)


def write_nifti(data: np.ndarray, geometry: VolumeGeometry, path: Path) -> Path:
    """Save an array with its geometry as NIfTI. The inverse of ``read_nifti``.

    The affine is rebuilt from spacing and origin with axes in the given
    orientation's positive directions (RAS by default), which is enough for
    every volume this project writes (synthetic data and derived masks).
    """
    nib = _nibabel()
    affine = np.eye(4)
    for i, s in enumerate(geometry.spacing_mm):
        affine[i, i] = s
    affine[:3, 3] = geometry.origin_mm
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(np.asarray(data), affine), str(path))
    return path


def read_dicom_series(folder: Path) -> tuple[np.ndarray, VolumeGeometry]:
    """Load a folder of single-slice DICOM files → (array, geometry).

    SimpleITK finds the series, sorts the slices by position and stacks
    them. Its arrays are indexed (z, y, x); we transpose to (x, y, z) so a
    volume reads the same whichever file format it came from. Only
    geometry-related metadata is kept — identifying tags are never read.
    """
    sitk = _sitk()
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(str(folder))
    if not series_ids:
        raise FileNotFoundError(f"No DICOM series found in {folder}")
    reader.SetFileNames(reader.GetGDCMSeriesFileNames(str(folder), series_ids[0]))
    image = reader.Execute()
    data = np.transpose(sitk.GetArrayFromImage(image), (2, 1, 0))
    spacing = tuple(float(s) for s in image.GetSpacing())
    origin = tuple(float(o) for o in image.GetOrigin())
    # DICOM's patient coordinate system is LPS; SimpleITK keeps it. Record it
    # honestly rather than pretend it is RAS; Phase 2 canonicalises.
    orientation = _orientation_code(np.asarray(image.GetDirection()).reshape(3, 3))
    geometry = VolumeGeometry(
        spacing_mm=spacing, shape=data.shape, orientation=orientation, origin_mm=origin
    )
    return data, geometry


def _orientation_code(direction: np.ndarray) -> str:
    """Three-letter axis code for a SimpleITK direction matrix (LPS world axes).

    For each image axis, find the world axis it mostly points along and
    whether it points to the positive end: +x = Left, +y = Posterior,
    +z = Superior; negative ends are Right, Anterior, Inferior.
    """
    letters = (("R", "L"), ("A", "P"), ("I", "S"))
    code = ""
    for col in range(3):
        world_axis = int(np.argmax(np.abs(direction[:, col])))
        positive = direction[world_axis, col] > 0
        code += letters[world_axis][1 if positive else 0]
    return code

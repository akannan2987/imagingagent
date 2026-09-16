"""Synthetic volumes: a stand-in for real MRI when the download is absent.

Each case is a small 3D volume containing a bright, blurred ellipsoid (a
hippocampus-like blob) on a darker, noisy background, plus the matching
label map (1 inside the ellipsoid, 0 outside). Cases vary in blob size,
position, orientation, intensity and noise so that segmentation and audit
code has something to get wrong. A fixed seed makes every run identical.

The generator can also write one case as a DICOM *series* — one file per
slice — so the DICOM reader is tested without any real patient data.

This is a crash-test dummy, not a patient: every case is labelled
``synthetic`` in its file name and its manifest record.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ...schemas import VolumeGeometry
from .io import write_nifti


@dataclass(frozen=True)
class SyntheticVolumeSpec:
    """Knobs for the generator. Defaults mimic MSD hippocampus crops."""

    shape: tuple[int, int, int] = (36, 50, 36)
    spacing_mm: tuple[float, float, float] = (1.0, 1.0, 1.0)
    radius_range_mm: tuple[float, float] = (6.0, 11.0)  # semi-axes
    blob_intensity: float = 0.75
    background_intensity: float = 0.25
    noise_sigma: float = 0.06
    blur_sigma_voxels: float = 1.0


def _gaussian_blur(volume: np.ndarray, sigma: float) -> np.ndarray:
    """Separable Gaussian blur in pure NumPy (no SciPy in the core)."""
    if sigma <= 0:
        return volume
    radius = int(3 * sigma)
    x = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-(x**2) / (2 * sigma**2))
    kernel /= kernel.sum()
    out = volume.astype(float)
    for axis in range(3):
        out = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), axis, out)
    return out


def make_case(
    rng: np.random.Generator, spec: SyntheticVolumeSpec
) -> tuple[np.ndarray, np.ndarray, VolumeGeometry]:
    """One (image, label, geometry) triple."""
    nx, ny, nz = spec.shape
    grid = np.stack(
        np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij"), axis=-1
    ).astype(float)
    centre = np.array([nx, ny, nz]) / 2 + rng.uniform(-3, 3, size=3)
    semi_axes = rng.uniform(*spec.radius_range_mm, size=3) / np.array(spec.spacing_mm)
    # A random rotation so blobs are not axis-aligned.
    q = rng.normal(size=(3, 3))
    rotation, _ = np.linalg.qr(q)
    local = (grid - centre) @ rotation
    inside = (local**2 / semi_axes**2).sum(axis=-1) <= 1.0
    label = inside.astype(np.uint8)

    image = np.full(spec.shape, spec.background_intensity, dtype=float)
    image[inside] = spec.blob_intensity * rng.uniform(0.85, 1.15)
    image = _gaussian_blur(image, spec.blur_sigma_voxels)
    image += rng.normal(0.0, spec.noise_sigma, size=spec.shape)
    image = np.clip(image, 0.0, 1.0).astype(np.float32)

    geometry = VolumeGeometry(spacing_mm=spec.spacing_mm, shape=spec.shape, orientation="RAS")
    return image, label, geometry


def generate_synthetic_volumes(
    out_dir: Path,
    n_cases: int,
    seed: int,
    spec: SyntheticVolumeSpec | None = None,
) -> list[tuple[str, Path, Path, VolumeGeometry]]:
    """Write ``n_cases`` image/label NIfTI pairs; return (case_id, image, label, geometry)."""
    spec = spec or SyntheticVolumeSpec()
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir)
    (out_dir / "imagesTr").mkdir(parents=True, exist_ok=True)
    (out_dir / "labelsTr").mkdir(parents=True, exist_ok=True)
    written = []
    for i in range(n_cases):
        image, label, geometry = make_case(rng, spec)
        case_id = f"synthetic_{i:03d}"
        image_path = write_nifti(image, geometry, out_dir / "imagesTr" / f"{case_id}.nii.gz")
        label_path = write_nifti(label, geometry, out_dir / "labelsTr" / f"{case_id}.nii.gz")
        written.append((case_id, image_path, label_path, geometry))
    return written


def write_synthetic_dicom_series(image: np.ndarray, geometry: VolumeGeometry, folder: Path) -> Path:
    """Write one volume as a DICOM series (one file per slice) for reader tests.

    Only geometry tags are set; no patient information exists to leak. The
    intensities are scaled to 16-bit integers as scanners store them.
    """
    try:
        import SimpleITK as sitk
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "SimpleITK is required: python -m pip install -r requirements-mri.txt"
        ) from exc

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    scaled = np.clip(image * 4000, 0, 65535).astype(np.uint16)
    sitk_image = sitk.GetImageFromArray(np.transpose(scaled, (2, 1, 0)))  # back to (z, y, x)
    sitk_image.SetSpacing(geometry.spacing_mm)
    sitk_image.SetOrigin(geometry.origin_mm)

    writer = sitk.ImageFileWriter()
    writer.KeepOriginalImageUIDOn()
    for z in range(sitk_image.GetDepth()):
        slice_image = sitk_image[:, :, z]
        slice_image.SetMetaData("0008|0060", "MR")  # modality
        slice_image.SetMetaData("0020|0013", str(z + 1))  # instance number
        slice_image.SetMetaData(
            "0020|0032",
            "\\".join(f"{v:.6f}" for v in sitk_image.TransformIndexToPhysicalPoint((0, 0, z))),
        )
        slice_image.SetMetaData("0020|0037", "1\\0\\0\\0\\1\\0")  # orientation (rows, cols)
        slice_image.SetMetaData(
            "0020|000e", "1.2.826.0.1.3680043.8.498.1"
        )  # one series UID for all slices
        slice_image.SetMetaData("0018|0050", f"{geometry.spacing_mm[2]:.6f}")  # slice thickness
        writer.SetFileName(str(folder / f"slice_{z:03d}.dcm"))
        writer.Execute(slice_image)
    return folder

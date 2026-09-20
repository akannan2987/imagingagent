"""pathology track, Phase 1: readers keep geometry; synthetic data; the manifest.

Every test needs requirements-pathology.txt and skips itself cleanly
without it, so the core suite still runs on a bare install.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import numpy as np
import pytest

from imagingagent.config import ProjectConfig
from imagingagent.ledger import RunLedger
from imagingagent.manifest import load_manifest
from imagingagent.schemas import Modality, TileGeometry, Track
from imagingagent.storage import LocalStorage

tifffile = pytest.importorskip("tifffile", reason="requirements-pathology.txt not installed")
PIL = pytest.importorskip("PIL", reason="requirements-pathology.txt not installed")
pq = pytest.importorskip("pyarrow.parquet", reason="requirements-pathology.txt not installed")
anndata = pytest.importorskip("anndata", reason="requirements-pathology.txt not installed")

from imagingagent.tracks.pathology.ingest import (
    deepliif_cases,
    ingest_pathology,
    kather_cases,
    mcmicro_cases,
    pannuke_cases,
    visium_cases,
)
from imagingagent.tracks.pathology.io import (
    DEEPLIIF_PANELS,
    read_deepliif_composite,
    read_markers_csv,
    read_ome_tiff,
    read_pannuke_tile,
    read_rgb_tile,
    read_visium_h5ad,
    write_ome_tiff,
    write_rgb_png,
)
from imagingagent.tracks.pathology.pannuke import extract_subset, read_index
from imagingagent.tracks.pathology.synth import (
    NUCLEUS_TYPES,
    TISSUE_CLASSES,
    SyntheticTileSpec,
    generate_synthetic_he,
    generate_synthetic_mif,
    generate_synthetic_spots,
    make_he_tile,
)

pytestmark = pytest.mark.pathology


# ---------------------------------------------------------------- readers ---


def test_rgb_tile_round_trip_and_geometry(tmp_path: Path) -> None:
    array = (np.random.default_rng(0).random((40, 60, 3)) * 255).astype(np.uint8)
    path = write_rgb_png(array, tmp_path / "t.png")
    again, geometry = read_rgb_tile(path, microns_per_pixel=0.495, stain="HE", magnification=20.0)
    np.testing.assert_array_equal(again, array)
    assert geometry.width == 60 and geometry.height == 40
    assert geometry.tile_area_mm2 == pytest.approx(40 * 60 * 0.495**2 / 1e6)
    tifffile.imwrite(str(tmp_path / "t.tif"), array)
    again_tif, _ = read_rgb_tile(tmp_path / "t.tif", 0.495)
    np.testing.assert_array_equal(again_tif, array)


def test_ome_tiff_keeps_pixel_size_and_channel_names(tmp_path: Path) -> None:
    data = (np.random.default_rng(1).random((3, 32, 48)) * 4000).astype(np.uint16)
    geometry = TileGeometry(
        microns_per_pixel=0.65, width=48, height=32, channels=["DAPI", "CD8", "PanCK"], stain="MIF"
    )
    path = write_ome_tiff(data, geometry, tmp_path / "x.ome.tif")
    again, g = read_ome_tiff(path)
    np.testing.assert_array_equal(again, data)
    assert g.channels == ["DAPI", "CD8", "PanCK"] and g.microns_per_pixel == pytest.approx(0.65)
    assert g.width == 48 and g.height == 32


def test_ome_tiff_without_metadata_uses_defaults(tmp_path: Path) -> None:
    data = np.zeros((2, 8, 8), dtype=np.uint16)
    tifffile.imwrite(str(tmp_path / "plain.tif"), data)
    with pytest.raises(ValueError, match="PhysicalSizeX"):
        read_ome_tiff(tmp_path / "plain.tif")
    _, g = read_ome_tiff(
        tmp_path / "plain.tif", channel_names=["A", "B"], default_microns_per_pixel=0.5
    )
    assert g.channels == ["A", "B"] and g.microns_per_pixel == 0.5


def test_deepliif_composite_splits_into_named_panels(tmp_path: Path) -> None:
    panels = [np.full((16, 16, 3), i * 40, dtype=np.uint8) for i in range(6)]
    write_rgb_png(np.concatenate(panels, axis=1), tmp_path / "c.png")
    split, geometry = read_deepliif_composite(tmp_path / "c.png")
    assert list(split) == list(DEEPLIIF_PANELS)
    assert split["Marker"][0, 0, 0] == 160 and geometry.width == 16
    write_rgb_png(np.zeros((16, 40, 3), dtype=np.uint8), tmp_path / "bad.png")
    with pytest.raises(ValueError, match="panels"):
        read_deepliif_composite(tmp_path / "bad.png")


def test_markers_csv(tmp_path: Path) -> None:
    (tmp_path / "markers.csv").write_text(
        "channel_number,cycle_number,marker_name\n1,1,DNA_1\n2,1,CD3\n", encoding="utf-8"
    )
    assert read_markers_csv(tmp_path / "markers.csv") == ["DNA_1", "CD3"]


# ------------------------------------------------------------- synthetic ---


def test_synthetic_he_tile_is_reproducible_and_labelled() -> None:
    a = make_he_tile(np.random.default_rng(3), SyntheticTileSpec(size=64), tissue_class=0)
    b = make_he_tile(np.random.default_rng(3), SyntheticTileSpec(size=64), tissue_class=0)
    np.testing.assert_array_equal(a["image"], b["image"])
    n = int(a["instances"].max())
    assert n > 0 and len(a["types"]) == n
    assert set(np.unique(a["instances"])) == set(range(n + 1))  # dense ids 0..n
    assert all(0 <= t < len(NUCLEUS_TYPES) for t in a["types"])
    assert (
        a["image"][a["instances"] > 0].mean() < a["image"][a["instances"] == 0].mean()
    )  # nuclei darker


def test_synthetic_generators_write_readable_files(tmp_path: Path) -> None:
    he = generate_synthetic_he(tmp_path / "he", 4, seed=9, spec=SyntheticTileSpec(size=64))
    assert [r["tissue_class"] for r in he] == list(TISSUE_CLASSES[:4])
    image, instances, types = read_pannuke_tile(he[0]["image_path"], he[0]["label_path"])
    assert image.shape == (64, 64, 3) and instances.max() == len(types)
    mif = generate_synthetic_mif(tmp_path / "mif", 1, seed=9, spec=SyntheticTileSpec(size=64))
    channels, g = read_ome_tiff(mif[0]["ome_path"])
    assert channels.shape == (4, 64, 64) and g.channels[0] == "DAPI"
    panels, _ = read_deepliif_composite(mif[0]["composite_path"])
    assert panels["IHC"].shape == (64, 64, 3)
    spots = generate_synthetic_spots(
        tmp_path / "spots",
        seed=9,
        n_side=6,
        spec=SyntheticTileSpec(size=120, microns_per_pixel=0.5),
    )
    adata, hires, g4 = read_visium_h5ad(spots["path"])
    assert adata.n_obs == 36 and adata.n_vars == 6 and hires.shape == (120, 120, 3)
    assert g4.microns_per_pixel == pytest.approx(0.5)


# ------------------------------------------------------------- pannuke ----


def _fake_pannuke_parquet(path: Path, n_rows: int = 5) -> None:
    """A tiny Parquet table with the mirror's schema: image / instances / categories / tissue."""
    import pyarrow as pa

    rng = np.random.default_rng(0)

    def png(arr: np.ndarray) -> dict:
        buf = io.BytesIO()
        PIL.Image.fromarray(arr).save(buf, format="PNG")
        return {"bytes": buf.getvalue(), "path": None}

    rows = []
    for r in range(n_rows):
        tile = (rng.random((16, 16, 3)) * 255).astype(np.uint8)
        masks = []
        for k in range(3):
            m = np.zeros((16, 16), dtype=np.uint8)
            m[k * 5 : k * 5 + 4, 2:6] = 255
            masks.append(png(m))
        rows.append(
            {"image": png(tile), "instances": masks, "categories": [0, 1, 4], "tissue": r % 19}
        )
    pq.write_table(pa.Table.from_pylist(rows), str(path))


def test_pannuke_extract_subset_is_seeded_and_readable(tmp_path: Path) -> None:
    parquet = tmp_path / "fold3-00000-of-00001.parquet"
    _fake_pannuke_parquet(parquet)
    rows = extract_subset(parquet, tmp_path / "extracted", n_tiles=3, seed=1, fold="fold3")
    again = extract_subset(parquet, tmp_path / "extracted2", n_tiles=3, seed=1, fold="fold3")
    assert [r["row"] for r in rows] == [r["row"] for r in again]
    assert all(r["n_nuclei"] == 3 for r in rows)
    index = read_index(tmp_path / "extracted", "fold3")
    assert len(index) == 3 and index[0]["case_id"].startswith("pannuke_fold3_")
    image, instances, types = read_pannuke_tile(
        tmp_path / "extracted" / "fold3" / "images" / f"{index[0]['case_id']}.png",
        tmp_path / "extracted" / "fold3" / "labels" / f"{index[0]['case_id']}.npz",
    )
    assert image.shape == (16, 16, 3) and instances.max() == 3 and list(types) == [0, 1, 4]


# ------------------------------------------------------------- ingestion ---


def _config(tmp_path: Path, **overrides) -> ProjectConfig:
    cfg = ProjectConfig()
    path_cfg = cfg.tracks.pathology.model_copy(update={"synthetic_tiles": 8, **overrides})
    tracks = cfg.tracks.model_copy(update={"pathology": path_cfg})
    return cfg.model_copy(
        update={"tracks": tracks, "storage": cfg.storage.model_copy(update={"base_dir": tmp_path})}
    )


def test_ingest_synthetic_covers_every_role(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    manifest, key = ingest_pathology(_config(tmp_path), storage, RunLedger(storage), synthetic=True)
    assert key == "data/processed/manifest_pathology.json" and manifest.synthetic
    roles = {c.tags["dataset_role"] for c in manifest.cases}
    assert roles == {"tissue", "nuclei", "ihc", "mif", "spatial"}
    assert all(
        c.track is Track.PATHOLOGY and c.modality is Modality.SYNTHETIC for c in manifest.cases
    )
    assert all(c.geometry is not None and c.geometry.kind == "tile" for c in manifest.cases)
    nuclei = [c for c in manifest.cases if c.tags["dataset_role"] == "nuclei"]
    assert nuclei and all(c.label_key for c in nuclei)
    assert all(storage.exists(c.image_key) for c in manifest.cases)
    assert load_manifest(storage, "pathology").case_ids == manifest.case_ids


def test_ingest_limit_and_roles(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    manifest, _ = ingest_pathology(
        _config(tmp_path), storage, RunLedger(storage), synthetic=True, limit=3, roles=["tissue"]
    )
    assert len(manifest) == 3 and {c.tags["dataset_role"] for c in manifest.cases} == {"tissue"}


def test_ingest_refuses_when_real_forced_but_absent(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    with pytest.raises(FileNotFoundError, match="No real data"):
        ingest_pathology(_config(tmp_path), storage, RunLedger(storage), synthetic=False)


def test_real_layouts_are_recognised(tmp_path: Path) -> None:
    """Fake each dataset's on-disk layout and check the role readers find and tag it."""
    raw = tmp_path / "data" / "raw"
    # Kather: class folders of .tif
    tile = (np.random.default_rng(0).random((20, 20, 3)) * 255).astype(np.uint8)
    for cls in ("01_TUMOR", "04_LYMPHO"):
        folder = raw / "kather2016" / "Kather_texture_2016_image_tiles_5000" / cls
        folder.mkdir(parents=True)
        tifffile.imwrite(str(folder / "1A_CRC-Prim-HE-01.tif"), tile)
        (folder / "._junk.tif").write_bytes(b"x")
    kather = kather_cases(raw, tmp_path, None)
    assert [c.tags["tissue_class"] for c in kather] == ["TUMOR", "LYMPHO"]
    assert kather[0].geometry.microns_per_pixel == pytest.approx(0.495)
    # PanNuke: extracted layout
    parquet = raw / "pannuke" / "fold3.parquet"
    parquet.parent.mkdir(parents=True)
    _fake_pannuke_parquet(parquet, 2)
    extract_subset(parquet, raw / "pannuke" / "extracted", 2, seed=0, fold="fold3")
    pannuke = pannuke_cases(raw, tmp_path, None)
    assert (
        len(pannuke) == 2
        and pannuke[0].label_key
        and pannuke[0].tags["licence"] == "CC-BY-NC-SA-4.0"
    )
    # DeepLIIF: composite PNGs
    comp = np.concatenate([np.full((16, 16, 3), 30 * i, dtype=np.uint8) for i in range(6)], axis=1)
    write_rgb_png(comp, raw / "deepliif" / "DeepLIIF_Validation_Set" / "case_a.png")
    deepliif = deepliif_cases(raw, tmp_path, None)
    assert (
        len(deepliif) == 1
        and deepliif[0].modality is Modality.IHC
        and deepliif[0].tags["label_panel"] == "Seg"
    )
    # MCMICRO: markers.csv + one OME-TIFF cycle file
    ex = raw / "mcmicro_exemplar001" / "exemplar-001"
    (ex / "raw").mkdir(parents=True)
    with (ex / "markers.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["channel_number", "cycle_number", "marker_name"])
        for i, name in enumerate(["DNA_6", "ELANE", "CD57", "CD45"], start=1):
            w.writerow([i, 6, name])
    geometry = TileGeometry(
        microns_per_pixel=0.65, width=24, height=24, channels=["a", "b", "c", "d"]
    )
    write_ome_tiff(
        np.zeros((4, 24, 24), dtype=np.uint16),
        geometry,
        ex / "raw" / "exemplar-001-cycle-06.ome.tiff",
    )
    mcmicro = mcmicro_cases(raw, tmp_path, None, default_mpp=0.65)
    assert len(mcmicro) == 1 and mcmicro[0].geometry.channels == ["DNA_6", "ELANE", "CD57", "CD45"]
    assert mcmicro[0].modality is Modality.MIF and mcmicro[0].tags["registered"] == "no"
    # Visium: an h5ad
    spots = generate_synthetic_spots(
        raw / "visium_hne", seed=0, n_side=4, spec=SyntheticTileSpec(size=80, microns_per_pixel=0.5)
    )
    spots["path"].rename(raw / "visium_hne" / "visium_hne_adata.h5ad")
    visium = visium_cases(raw, tmp_path)
    assert (
        len(visium) == 1
        and visium[0].modality is Modality.SPATIAL_TRANSCRIPTOMICS
        and visium[0].tags["n_spots"] == "16"
    )
    # And the whole thing through ingest, real data winning over synthetic
    storage = LocalStorage(tmp_path)
    manifest, _ = ingest_pathology(_config(tmp_path), storage, RunLedger(storage))
    assert not manifest.synthetic and not any(c.synthetic for c in manifest.cases)
    assert manifest.dataset == "kather2016,pannuke,deepliif,mcmicro_exemplar001,visium_hne"

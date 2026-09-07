"""Command line: every command runs and says what it did."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from imagingagent import __version__
from imagingagent.cli import app

runner = CliRunner()


def _write_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "paths:\n"
        f"  raw: {(tmp_path / 'raw').as_posix()}\n"
        f"  interim: {(tmp_path / 'interim').as_posix()}\n"
        f"  processed: {(tmp_path / 'processed').as_posix()}\n"
        f"  runs: {(tmp_path / 'runs').as_posix()}\n"
        f"  models: {(tmp_path / 'models').as_posix()}\n"
        "storage:\n"
        "  backend: local\n"
        f"  base_dir: {tmp_path.as_posix()}\n",
        encoding="utf-8",
    )
    return cfg


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_doctor_is_healthy(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--config", str(_write_config(tmp_path))])
    assert result.exit_code == 0, result.stdout
    assert "result       : healthy" in result.stdout


def test_init_creates_folders_and_ledger(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    result = runner.invoke(app, ["init", "--config", str(cfg)])
    assert result.exit_code == 0, result.stdout
    for name in ("raw", "interim", "processed", "runs", "models"):
        assert (tmp_path / name).is_dir()
    assert (tmp_path / "runs" / "ledger.jsonl").is_file()

    listed = runner.invoke(app, ["ledger", "list", "--config", str(cfg)])
    assert listed.exit_code == 0
    assert "init" in listed.stdout and "finished" in listed.stdout


def test_config_show_prints_json(tmp_path: Path) -> None:
    result = runner.invoke(app, ["config", "show", "--config", str(_write_config(tmp_path))])
    assert result.exit_code == 0
    assert '"review_budget_fraction": 0.1' in result.stdout


def test_missing_config_is_a_clean_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--config", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 2


# --- Phase 0c: track-aware commands -----------------------------------------


def test_doctor_lists_both_tracks_and_serve(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--config", str(_write_config(tmp_path))])
    assert result.exit_code == 0, result.stdout
    assert "tracks       : mri, pathology" in result.stdout
    for heading in ("[mri]", "[pathology]", "[serve]"):
        assert heading in result.stdout


def test_doctor_can_filter_one_track(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["doctor", "--config", str(_write_config(tmp_path)), "--track", "pathology"]
    )
    assert result.exit_code == 0, result.stdout
    assert "[pathology]" in result.stdout and "[mri]" not in result.stdout


def test_unknown_track_is_a_clean_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["doctor", "--config", str(_write_config(tmp_path)), "--track", "ultrasound"]
    )
    assert result.exit_code == 2


def test_tracks_command_shows_datasets(tmp_path: Path) -> None:
    result = runner.invoke(app, ["tracks", "--config", str(_write_config(tmp_path))])
    assert result.exit_code == 0, result.stdout
    assert "msd_task04_hippocampus" in result.stdout
    assert "pannuke" in result.stdout and "role=nuclei" in result.stdout
    assert "review budget 10%" in result.stdout


def test_modalities_command_lists_implemented_and_planned() -> None:
    result = runner.invoke(app, ["modalities"])
    assert result.exit_code == 0, result.stdout
    assert "MRI" in result.stdout and "implemented" in result.stdout
    assert "PET" in result.stdout and "planned" in result.stdout
    only_pathology = runner.invoke(app, ["modalities", "--track", "pathology"])
    assert "HE" in only_pathology.stdout and "PET" not in only_pathology.stdout


def test_ledger_list_filters_by_track(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    runner.invoke(app, ["init", "--config", str(cfg)])  # writes a 'shared' run
    shared = runner.invoke(app, ["ledger", "list", "--config", str(cfg), "--track", "pathology"])
    assert "no runs recorded" in shared.stdout
    everything = runner.invoke(app, ["ledger", "list", "--config", str(cfg)])
    assert "shared" in everything.stdout

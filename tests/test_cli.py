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

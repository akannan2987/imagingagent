"""The command line: ``imagingagent <command>``.

Design rule: the command line is a thin skin. Every command calls the same
package functions that a future HTTP server or MCP server will call, so
"run it by hand" and "run it through an agent" are the same code path with
different front doors. Nothing lives only in this file.

Commands in Phase 0:

    imagingagent version          print the package version
    imagingagent doctor           check the environment and folders
    imagingagent init             create the data/run folders from the config
    imagingagent config show      print the validated configuration
    imagingagent ledger list      show the run history
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .config import ENV_CONFIG_VAR, ProjectConfig, load_config, resolve_config_path
from .ledger import RunLedger
from .storage import get_storage
from .utils import platform_summary

app = typer.Typer(
    name="imagingagent",
    help="A quantitative imaging pipeline built to be operated by an agent.",
    no_args_is_help=True,
    add_completion=False,
)
config_app = typer.Typer(help="Inspect the configuration.", no_args_is_help=True)
ledger_app = typer.Typer(help="Inspect the run ledger.", no_args_is_help=True)
app.add_typer(config_app, name="config")
app.add_typer(ledger_app, name="ledger")

ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        "-c",
        help=f"Path to a YAML config. Falls back to ${ENV_CONFIG_VAR}, then built-in defaults.",
        exists=False,
        dir_okay=False,
    ),
]

# Optional libraries that later phases need. ``doctor`` reports which are
# present so a reader knows immediately what a failing command is missing.
OPTIONAL_MODULES: dict[str, str] = {
    "nibabel": "Phase 1 — NIfTI reading",
    "SimpleITK": "Phase 1/2 — DICOM reading, registration",
    "skimage": "Phase 2/3 — denoising, classical segmentation",
    "torch": "Phase 3 — deep learning",
    "monai": "Phase 3/4 — medical imaging transforms and metrics",
    "sklearn": "Phase 4 — failure predictor",
    "mcp": "Phase 6 — Model Context Protocol server",
    "streamlit": "Phase 6 — review queue interface",
}


def _load(config: Path | None) -> ProjectConfig:
    try:
        return load_config(config)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(f"imagingagent {__version__}")


@app.command()
def doctor(config: ConfigOption = None) -> None:
    """Check Python, the configuration, the folders and optional libraries.

    Exit code 0 means the core is healthy. Missing optional libraries are
    reported but do not fail the check: each phase installs its own.
    """
    problems = 0
    typer.echo(f"imagingagent {__version__}")
    typer.echo(f"platform     : {platform_summary()}")

    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 11)
    typer.echo(f"python       : {major}.{minor} {'ok' if ok else 'TOO OLD (need 3.11+)'}")
    problems += 0 if ok else 1

    source = resolve_config_path(config)
    cfg = _load(config)
    typer.echo(f"config       : {'built-in defaults' if source is None else source}")
    typer.echo(f"config hash  : {cfg.content_hash()[:12]}")

    for folder in cfg.paths.all():
        state = "present" if folder.is_dir() else "missing (run: imagingagent init)"
        typer.echo(f"folder       : {folder.as_posix():<18} {state}")

    for module, purpose in OPTIONAL_MODULES.items():
        try:
            importlib.import_module(module)
            state = "installed"
        except ImportError:
            state = "not installed"
        typer.echo(f"optional     : {module:<10} {state:<14} ({purpose})")

    typer.echo("result       : " + ("healthy" if problems == 0 else f"{problems} problem(s)"))
    raise typer.Exit(code=0 if problems == 0 else 1)


@app.command()
def init(config: ConfigOption = None) -> None:
    """Create every folder the configuration refers to (safe to rerun)."""
    cfg = _load(config)
    for folder in cfg.paths.all():
        existed = folder.is_dir()
        folder.mkdir(parents=True, exist_ok=True)
        typer.echo(f"{'exists ' if existed else 'created'}  {folder.as_posix()}")
    storage = get_storage(cfg.storage)
    ledger = RunLedger(storage)
    record = ledger.start(command="init", config=cfg)
    ledger.finish(record)
    typer.echo(f"ledger   {ledger.key} (run {record.run_id})")


@config_app.command("show")
def config_show(config: ConfigOption = None) -> None:
    """Print the validated configuration as JSON, defaults filled in."""
    cfg = _load(config)
    typer.echo(cfg.model_dump_json(indent=2))


@ledger_app.command("list")
def ledger_list(config: ConfigOption = None) -> None:
    """List runs recorded in the ledger, oldest first."""
    cfg = _load(config)
    ledger = RunLedger(get_storage(cfg.storage))
    runs = ledger.latest_per_run()
    if not runs:
        typer.echo("no runs recorded yet (try: imagingagent init)")
        return
    typer.echo(f"{'run_id':<14}{'started_at':<22}{'command':<12}{'status':<10}config")
    for record in runs.values():
        typer.echo(
            f"{record.run_id:<14}{record.started_at:<22}{record.command:<12}"
            f"{record.status:<10}{record.config_hash[:12]}"
        )


if __name__ == "__main__":  # pragma: no cover
    app()

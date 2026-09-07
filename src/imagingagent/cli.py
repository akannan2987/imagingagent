"""The command line: ``imagingagent <command>``.

Design rule: the command line is a thin skin. Every command calls the same
package functions that a future HTTP server or MCP server will call, so
"run it by hand" and "run it through an agent" are the same code path with
different front doors. Nothing lives only in this file.

Track-aware commands take ``--track mri`` or ``--track pathology``; a
command run against a disabled track refuses with a clear message.

Commands in Phase 0c:

    imagingagent version               print the package version
    imagingagent doctor [--track T]    check the environment, folders, extras
    imagingagent init                  create the data/run folders from the config
    imagingagent tracks                show both tracks and their key settings
    imagingagent modalities [--track]  list every modality: implemented or planned
    imagingagent config show           print the validated configuration
    imagingagent ledger list [--track] show the run history
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .config import ENV_CONFIG_VAR, TRACK_NAMES, ProjectConfig, load_config, resolve_config_path
from .ledger import RunLedger
from .modality import specs_for_track
from .schemas import Track
from .storage import get_storage
from .utils import platform_summary

app = typer.Typer(
    name="imagingagent",
    help="A quantitative imaging platform — MRI volumes and pathology slides — built to be operated by an agent.",
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
TrackOption = Annotated[
    str | None,
    typer.Option("--track", "-t", help="Limit to one track: 'mri' or 'pathology'."),
]

# Optional libraries, grouped by the track (or serving layer) that needs them.
# ``doctor`` reports which are present so a failing command explains itself.
OPTIONAL_MODULES: dict[str, dict[str, str]] = {
    "mri": {
        "nibabel": "Phase 1 — NIfTI reading",
        "SimpleITK": "Phase 1/2 — DICOM reading, registration",
        "skimage": "Phase 2/3 — denoising, classical segmentation",
        "torch": "Phase 3 — deep learning",
        "monai": "Phase 3/4 — transforms, U-Net, metrics",
    },
    "pathology": {
        "tifffile": "Phase 1 — TIFF / OME-TIFF reading",
        "tiffslide": "Phase 1 — pyramidal slides (pure Python)",
        "openslide": "Phase 1 — vendor slide formats (optional)",
        "skimage": "Phase 2/3 — stain separation, classical segmentation",
        "instanseg": "Phase 3 — pre-trained nucleus/cell model",
        "transformers": "Phase 6 — foundation-model embeddings",
        "torch_geometric": "Phase 7 — graph neural networks",
        "squidpy": "Phase 7/8 — spatial statistics, Visium",
    },
    "serve": {
        "mcp": "Phase 11 — Model Context Protocol server",
        "streamlit": "Phase 11 — review interface",
    },
}


def _load(config: Path | None) -> ProjectConfig:
    try:
        return load_config(config)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


def _validate_track(track: str | None) -> str | None:
    if track is not None and track not in TRACK_NAMES:
        typer.echo(
            f"error: unknown track {track!r}; expected one of {', '.join(TRACK_NAMES)}", err=True
        )
        raise typer.Exit(code=2)
    return track


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(f"imagingagent {__version__}")


@app.command()
def doctor(config: ConfigOption = None, track: TrackOption = None) -> None:
    """Check Python, the configuration, the folders and optional libraries.

    Exit code 0 means the core is healthy. Missing optional libraries are
    reported per track but do not fail the check: each phase installs its own.
    """
    track = _validate_track(track)
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
    typer.echo(f"tracks       : {', '.join(cfg.tracks.enabled_names()) or 'none enabled'}")

    for folder in cfg.paths.all():
        state = "present" if folder.is_dir() else "missing (run: imagingagent init)"
        typer.echo(f"folder       : {folder.as_posix():<18} {state}")

    groups = [track] if track else list(OPTIONAL_MODULES)
    for group in groups:
        typer.echo(f"[{group}]")
        for module, purpose in OPTIONAL_MODULES[group].items():
            try:
                importlib.import_module(module)
                state = "installed"
            except ImportError:
                state = "not installed"
            typer.echo(f"  optional   : {module:<16} {state:<14} ({purpose})")

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


@app.command()
def tracks(config: ConfigOption = None) -> None:
    """Show both tracks: enabled or not, and their key settings."""
    cfg = _load(config)
    mri = cfg.tracks.mri
    typer.echo(f"mri         : {'enabled' if mri.enabled else 'disabled'}")
    typer.echo(f"  dataset   : {mri.dataset.name} ({mri.dataset.modality}, {mri.dataset.licence})")
    typer.echo(f"  spacing   : {mri.target_spacing_mm} mm")
    typer.echo(
        f"  synthetic : {'fallback on' if mri.dataset.use_synthetic_fallback else 'off'} ({mri.dataset.synthetic_cases} cases, seed {mri.dataset.seed})"
    )
    path = cfg.tracks.pathology
    typer.echo(f"pathology   : {'enabled' if path.enabled else 'disabled'}")
    for entry in path.datasets:
        typer.echo(
            f"  dataset   : {entry.name:<22} role={entry.role:<8} {'on ' if entry.enabled else 'off'}  {entry.licence}"
        )
    typer.echo(f"  resolution: {path.target_microns_per_pixel} µm/px")
    typer.echo(
        f"  synthetic : {'fallback on' if path.use_synthetic_fallback else 'off'} ({path.synthetic_tiles} tiles, seed {path.seed})"
    )
    typer.echo(f"audit       : review budget {cfg.audit.review_budget_fraction:.0%}")


@app.command()
def modalities(track: TrackOption = None) -> None:
    """List every modality the platform knows about, implemented or planned."""
    track = _validate_track(track)
    chosen = [Track(track)] if track else [Track.MRI, Track.PATHOLOGY]
    typer.echo(f"{'modality':<24}{'track':<11}{'geometry':<9}{'status':<13}description")
    for t in chosen:
        for spec in specs_for_track(t):
            if spec.track is Track.SHARED and t is not chosen[0]:
                continue  # print the shared SYNTHETIC entry once
            typer.echo(
                f"{spec.name:<24}{spec.track.value:<11}{spec.geometry:<9}{spec.status:<13}{spec.description}"
            )


@config_app.command("show")
def config_show(config: ConfigOption = None) -> None:
    """Print the validated configuration as JSON, defaults filled in."""
    cfg = _load(config)
    typer.echo(cfg.model_dump_json(indent=2))


@ledger_app.command("list")
def ledger_list(config: ConfigOption = None, track: TrackOption = None) -> None:
    """List runs recorded in the ledger, oldest first, optionally for one track."""
    track = _validate_track(track)
    cfg = _load(config)
    ledger = RunLedger(get_storage(cfg.storage))
    runs = ledger.latest_per_run()
    if track:
        runs = {k: v for k, v in runs.items() if v.track.value == track}
    if not runs:
        typer.echo("no runs recorded yet (try: imagingagent init)")
        return
    typer.echo(f"{'run_id':<14}{'started_at':<22}{'command':<12}{'track':<11}{'status':<10}config")
    for record in runs.values():
        typer.echo(
            f"{record.run_id:<14}{record.started_at:<22}{record.command:<12}"
            f"{record.track.value:<11}{record.status:<10}{record.config_hash[:12]}"
        )


if __name__ == "__main__":  # pragma: no cover
    app()

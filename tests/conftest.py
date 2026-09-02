"""Shared test fixtures.

A fixture is a small, reusable setup step. ``tmp_path`` (built into pytest)
gives every test its own empty temporary folder, so tests never touch the
real data/ or runs/ folders and never interfere with each other.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from imagingagent.config import ENV_CONFIG_VAR, ProjectConfig, StorageConfig
from imagingagent.storage import LocalStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    """A local storage backend rooted in a throw-away folder."""
    return LocalStorage(tmp_path / "store")


@pytest.fixture
def config(tmp_path: Path) -> ProjectConfig:
    """A configuration whose folders all live under the temporary folder."""
    cfg = ProjectConfig()
    cfg = cfg.model_copy(
        update={
            "paths": cfg.paths.model_copy(
                update={
                    name: tmp_path / name
                    for name in ("raw", "interim", "processed", "runs", "models")
                }
            ),
            "storage": StorageConfig(backend="local", base_dir=tmp_path),
        }
    )
    return cfg


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure a developer's own environment variable never leaks into tests."""
    if ENV_CONFIG_VAR in os.environ:
        monkeypatch.delenv(ENV_CONFIG_VAR)

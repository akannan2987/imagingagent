"""Configuration: defaults, YAML overrides, validation and hashing."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from imagingagent.config import ENV_CONFIG_VAR, ProjectConfig, load_config


def test_defaults_are_valid() -> None:
    cfg = ProjectConfig()
    assert cfg.project_name == "imagingagent"
    assert cfg.audit.review_budget_fraction == pytest.approx(0.10)
    assert cfg.paths.raw == Path("data/raw")


def test_repo_default_yaml_matches_builtin_defaults() -> None:
    """configs/default.yaml must say the same thing as the code defaults.

    If someone edits one and forgets the other, this test catches it.
    """
    repo_default = Path(__file__).resolve().parents[1] / "configs" / "default.yaml"
    assert repo_default.exists(), "configs/default.yaml is missing"
    assert load_config(repo_default).content_hash() == ProjectConfig().content_hash()


def test_yaml_override(tmp_path: Path) -> None:
    yaml_path = tmp_path / "custom.yaml"
    yaml_path.write_text("audit:\n  review_budget_fraction: 0.25\n", encoding="utf-8")
    cfg = load_config(yaml_path)
    assert cfg.audit.review_budget_fraction == pytest.approx(0.25)
    # Everything not mentioned keeps its default.
    assert cfg.dataset.name == "msd_task04_hippocampus"


def test_environment_variable_is_honoured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    yaml_path = tmp_path / "env.yaml"
    yaml_path.write_text("project_name: from-env\n", encoding="utf-8")
    monkeypatch.setenv(ENV_CONFIG_VAR, str(yaml_path))
    assert load_config().project_name == "from-env"


def test_out_of_range_value_is_rejected(tmp_path: Path) -> None:
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text("audit:\n  review_budget_fraction: 10\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(yaml_path)


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    """A misspelled key must fail loudly, not be silently ignored."""
    yaml_path = tmp_path / "typo.yaml"
    yaml_path.write_text("audit:\n  reveiw_budget_fraction: 0.1\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(yaml_path)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_hash_is_stable_and_sensitive() -> None:
    a = ProjectConfig()
    b = ProjectConfig()
    c = ProjectConfig(project_name="other")
    assert a.content_hash() == b.content_hash()
    assert a.content_hash() != c.content_hash()
    assert len(a.content_hash()) == 64

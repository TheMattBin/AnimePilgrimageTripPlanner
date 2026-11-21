"""Tests for Settings configuration and root-relative cache resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from anime_pilgrimage.config import Settings, _find_project_root


def test_empty_cache_dir_env_var_falls_back_to_repo_root_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Regression test: CACHE_DIR= must coerce to None, not Path('.')."""
    repo_root = _find_project_root()
    monkeypatch.setenv("CACHE_DIR", "")
    monkeypatch.chdir(tmp_path)

    settings = Settings()
    assert settings.cache_dir is None
    assert settings.resolved_cache_dir == repo_root / ".cache"
    assert settings.resolved_cache_dir != Path(".")
    assert settings.resolved_cache_dir != tmp_path

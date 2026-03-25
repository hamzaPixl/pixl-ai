"""Shared test fixtures for pixl-cli tests."""

from __future__ import annotations

import pixl.paths
import pytest


@pytest.fixture(autouse=True)
def _isolate_global_pixl(tmp_path: "pytest.TempPathFactory", monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from polluting ~/.pixl/.

    Redirects all global pixl storage to a temp directory so tests
    never write to the real ~/.pixl/projects/ or ~/.pixl/projects.json.
    """
    fake_global = tmp_path / "_pixl_global"
    fake_global.mkdir()
    monkeypatch.setattr(pixl.paths, "_global_pixl_dir_override", fake_global)

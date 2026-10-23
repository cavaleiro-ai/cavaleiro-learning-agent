"""Locate a workflow file by name across the active and the disabled workflow directories.

Cavaleiro Learning Agent keeps the workflows that publish, sign, deploy, or need upstream
credentials in ``.github/workflows-disabled/`` (see its README) so a fork never publishes under
the upstream identity. Their contracts (job graphs, gates, R2 steps) are still tested from there.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIRS = (ROOT / ".github" / "workflows", ROOT / ".github" / "workflows-disabled")


def workflow_path(name: str) -> Path:
    """The workflow file *name*, from ``workflows/`` first, else from ``workflows-disabled/``."""
    for directory in WORKFLOW_DIRS:
        if (directory / name).is_file():
            return directory / name
    return WORKFLOW_DIRS[0] / name


def all_workflow_files() -> list[Path]:
    """Every workflow file in both directories, sorted by path."""
    return sorted(path for directory in WORKFLOW_DIRS for path in directory.glob("*.y*ml"))

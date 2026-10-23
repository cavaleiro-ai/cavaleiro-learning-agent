"""search_files filters directory hits through git without running the searched repo's programs.

Regression for #137582. ``search_files(target="files")`` drops gitignored directory hits with
``git check-ignore`` in whatever directory the model chose as the search root. ``check-ignore``
reads the index, so git ran the repository's ``core.fsmonitor`` program: searching a tree that
carries an armed ``.git/config`` (a downloaded repo, a synced folder, or one the agent itself was
told to write) executed that program as the user, before any approval prompt. The probe now pins
``core.fsmonitor=false`` like every other automatic git call (GHSA-7x36-8jrh-v4pw).

On native Windows the same filter never ran at all: the root went to the native ``git.exe`` in the
Git Bash ``/c/...`` form, which it cannot read (Hermes disables MSYS argv conversion), so git failed
and every gitignored directory leaked into the results. Root and paths now use the drive form there.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import PureWindowsPath

import pytest

from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

_CLEAN_GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
                  "GIT_CONFIG_NOSYSTEM": "1"}


@pytest.fixture
def armed_repo(tmp_path):
    """A repo with one ignored directory whose .git/config names an fsmonitor program that leaves
    a marker file."""
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_CLEAN_GIT_ENV)
    for name in ("somedir", "ignored_dir"):
        (repo / name).mkdir()
        (repo / name / "f.txt").write_text("x\n")
    (repo / ".gitignore").write_text("ignored_dir/\n")
    marker = tmp_path / "FSMARKER"
    subprocess.run(["git", "-C", str(repo), "config", "core.fsmonitor", f"touch '{marker.as_posix()}'"],
                   check=True, env=_CLEAN_GIT_ENV)
    return repo, marker


def _ops(repo):
    return ShellFileOperations(LocalEnvironment(cwd=str(repo)), cwd=str(repo))


def test_baseline_unhardened_check_ignore_runs_fsmonitor(armed_repo):
    """Sanity: the repo is armed, so a plain ``check-ignore`` fires the payload."""
    repo, marker = armed_repo
    subprocess.run(["git", "-C", str(repo), "check-ignore", "--stdin"], input="somedir\n", text=True,
                   capture_output=True, check=False, env=_CLEAN_GIT_ENV)
    assert marker.exists()


def test_gitignore_filter_drops_ignored_paths_without_running_repo_fsmonitor(armed_repo):
    repo, marker = armed_repo
    kept = _ops(repo)._filter_gitignored_paths(["somedir", "ignored_dir"], str(repo))
    assert not marker.exists()
    assert kept == ["somedir"]


def test_directory_supplement_skips_ignored_dirs_without_running_repo_fsmonitor(armed_repo):
    """The rg lane's directory supplement (find + the git filter), as search_files runs it."""
    repo, marker = armed_repo
    dirs, _limit_reason = _ops(repo)._search_directories_with_find("*dir", str(repo), 10)
    names = {PureWindowsPath(item).name for item in dirs}
    assert "somedir" in names
    assert "ignored_dir" not in names
    assert not marker.exists()

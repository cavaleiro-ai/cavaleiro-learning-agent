"""The managed llama-server's endpoint key stays out of its argv and out of llama-server.log.

Regression for #137804. The supervisor passed the key as ``--api-key <value>`` and wrote the whole
command line to ``llama-server.log`` as ``# spawn: [...]`` on every spawn and crash-restart. The
log bypasses ``RedactingFormatter``, so the key accumulated at rest (and travelled with any log
attached to a bug report), and other local users could read it from the process list. The key is
already persisted beside the runtimes, so llama-server now reads it with ``--api-key-file``; the
argv form survives only when that file cannot hold the key, and the log line masks it either way.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from hermes_cli.local_runtime import supervisor


def _spawned(tmp_path, monkeypatch, port: int):
    monkeypatch.setattr(supervisor, "runtimes_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(supervisor, "_direct_io_args", lambda exe: ())
    commands = []
    monkeypatch.setattr(supervisor, "spawn_server", lambda argv, **kwargs: (
        commands.append(argv) or SimpleNamespace(pid=123, poll=lambda: 0), None,
    ))
    sup = supervisor.LlamaServerSupervisor(tmp_path / "engine" / "llama-server", tmp_path / "models", port=port)
    monkeypatch.setattr(sup, "_write_state", lambda: None)
    try:
        sup._spawn()
    finally:
        sup.stop()
    return sup, commands[0]


def test_spawn_passes_the_key_by_file_and_never_logs_it(tmp_path, monkeypatch):
    sup, argv = _spawned(tmp_path, monkeypatch, 19011)
    assert sup.api_key not in argv
    assert "--api-key" not in argv
    key_file = Path(argv[argv.index("--api-key-file") + 1])
    assert key_file.read_text(encoding="utf-8") == sup.api_key
    log = sup.log_path.read_text(encoding="utf-8")
    assert "# spawn:" in log
    assert sup.api_key not in log


def test_unpersisted_key_falls_back_to_argv_but_is_masked_in_the_log(tmp_path, monkeypatch):
    # _stable_api_key could not write the key file (read-only home): the key exists only in memory.
    monkeypatch.setattr(supervisor, "_stable_api_key", lambda: "k" * 32)
    sup, argv = _spawned(tmp_path, monkeypatch, 19012)
    assert argv[argv.index("--api-key") + 1] == "k" * 32
    log = sup.log_path.read_text(encoding="utf-8")
    assert "# spawn:" in log
    assert "k" * 32 not in log

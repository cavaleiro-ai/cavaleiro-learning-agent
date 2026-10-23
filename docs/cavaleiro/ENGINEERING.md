# Cavaleiro Learning Agent 1.0.0 — engineering report

This report records how Cavaleiro Learning Agent 1.0.0 was derived from the original project, what was found, what was changed, and how each change was verified. It is written for maintainers and reviewers.

| | |
|---|---|
| Original project | branch `main`, MIT License |
| Original project commit | `e6cf2a9b1e8f98d40408b09a9a55993c8459b4b4` (2026-10-17, "fix(gateway): a declared group-chat allowlist alone no longer silences DM pairing") |
| Derivative | `cavaleiro-ai/cavaleiro-learning-agent`, release 1.0.0, 2026-10-17 |
| Verification host | Windows 10 Pro (native, Git Bash for the shell backend), Python 3.14.3, uv 0.11.3, git 2.x; ripgrep not on `PATH` |

**Contents:** [Architecture map](#architecture-map) · [Baseline](#baseline) · [Findings](#findings) · [Improvements and verification](#improvements-and-verification) · [Rebrand and fork safety](#rebrand-and-fork-safety) · [Not done, and why](#not-done-and-why) · [Known limitations](#known-limitations) · [Next steps](#recommended-next-steps)

---

## Architecture map

Cavaleiro Learning Agent is a Python 3.14 personal agent (≈20,000 tracked files, ≈6,600 pytest files) with TypeScript front ends. One agent core serves every entry point. Former "god files" are split into a **facade** plus `<stem>_<topic>.py` **siblings** (for example `hermes_state.py` + 60 `hermes_state_*.py`, `run_agent.py` + `agent/turn_*.py`); a code-health ratchet (`scripts/code_health/`) caps function complexity and file size.

```text
 Entry points ──────────────────────────────────────────────────────────────────────
  hermes (hermes_cli/main.py) · cli.py REPL · gateway/run.py · tui_gateway/ (+ ui-tui, apps/desktop)
  acp_adapter/ (IDEs) · cron/scheduler.py · batch_runner.py · mcp_serve.py
        │
        ▼
 Agent core: AIAgent (run_agent.py) → agent/conversation_loop.py, agent/turn_*.py
  prompt assembly (agent/prompt_builder.py) · provider resolution (hermes_cli/runtime_provider*.py,
  providers/) · context compression (agent/context_compressor.py) · prompt caching invariants
        │ tool calls                                   │ persistence / learning
        ▼                                              ▼
 Tools: tools/registry.py, model_tools.py, toolsets.py   State: hermes_state*.py (SQLite, FTS5, WAL)
  terminal_tool*.py → tools/environments/ (local,         Memory: tools/memory_tool*.py (file store
   docker, ssh, modal, daytona, singularity, vercel)       with sidecar lock), plugins/memory/
  approval floors: approval.py, approval_floors.py,        Skills: skills/, optional-skills/,
   approval_detection.py, shell_heredoc.py                  tools/skill*_*.py, agent/curator*.py
  file tools: file_operations*.py, file_tools*.py         Sessions/gateway: gateway/session*.py
  web, browser, MCP (mcp_tool*.py), delegate, vision      Config/secrets: ~/.hermes/config.yaml,
                                                            .env (secrets only), auth.json
```

| Area | Entry points / key modules | Notes |
|---|---|---|
| CLI and setup | `hermes_cli/main.py`, `hermes_cli/subcommands/`, `hermes_cli/setup*.py`, `hermes_cli/config*.py` | `hermes` console script; `DEFAULT_CONFIG` in `config_defaults.py`; `.env` holds secrets only |
| Agent loop | `run_agent.py`, `agent/` | Three API modes (chat completions, Codex responses, Anthropic messages); compression is the only allowed mid-conversation prompt mutation |
| Tools | `tools/registry.py`, `model_tools.py`, `toolsets.py` | Tools self-register at import; toolsets per platform |
| Tool execution safety | `tools/approval*.py`, `tools/approval_detection.py`, `tools/shell_heredoc.py`, `tools/terminal_tool_guards.py`, `tools/path_security.py`, `tools/url_safety.py` | Hardline blocklist and user `approvals.deny` run before yolo/`mode: off`; dangerous-pattern detection prompts; smart mode asks a guardian model |
| Gateway | `gateway/run*.py`, `gateway/slash_commands*.py`, `gateway/platforms/`, `plugins/platforms/` | ~25 messaging platforms, allowlists, DM pairing, multiplexed profiles |
| State and memory | `hermes_state*.py`, `tools/memory_tool_store.py`, `plugins/memory/` | SQLite sessions with FTS5; `MEMORY.md`/`USER.md` with a file lock and drift detection |
| Local models | `hermes_cli/local_runtime/` | Supervises a llama.cpp `llama-server` router on `127.0.0.1` with a stable per-install key |
| Extension points | `plugins/` (memory, context engine, model providers, platforms, image gen), skills (`SKILL.md`), MCP servers, hooks | Plugins are the preferred way to add capability |
| Environment manager | `pm/`, `setup-hermes.{sh,ps1}`, `activate*` | Own dependency manager over a pinned `uv`; `uv.lock` is authoritative; exact pins |
| Tests | `tests/` (mirrors the source tree), `tests-js/`, `scripts/run_tests.sh` → `scripts/run_tests_parallel.py` | Per-file subprocess isolation, credentials blanked, `HERMES_HOME` sandboxed, `@pytest.mark.platforms(...)` for host-specific tests |
| CI and release | `.github/workflows/ci.yaml` (orchestrator of reusable test/lint workflows), release workflows (now in `.github/workflows-disabled/`) | Blacksmith runners; releases publish to GitHub, Docker Hub, Cloudflare R2, the Microsoft Store, and a signed Termux APT repo |
| Docs | `website/` (Docusaurus), `AGENTS.md` per area | Not deployed by this repository (deploy workflow disabled) |

---

## Baseline

**Environment.** `uv sync --frozen --python 3.14 --group dev --group test` in the checkout (project-local `.venv`, 1 m 23 s). The project's own `pm.build_env` produces the same groups; uv was used as the project hints suggest. The canonical runner was used for every recorded run, with `HERMES_PYTHON` pointing at that interpreter:

```bash
export HERMES_PYTHON="$PWD/.venv/Scripts/python.exe"
bash scripts/run_tests.sh -j 4 $(cat subset.txt)
```

**Why a subset.** Each test file runs in a fresh subprocess, and on this host every subprocess spent 30–70 s importing (cProfile: 27 s of 45 s in `importlib` `get_data`, i.e. reading `.pyc` files under real-time antivirus scanning, with ten agents sharing the machine). The full suite (≈6,600 files) would take many hours, so a targeted subset covering every area touched was chosen (49 files):

- approval floors: `tests/tools/test_approval.py`, `test_approval_deny_rules.py`, `test_approval_grep_in_substitution.py`, `test_hardline_blocklist.py`, `test_hardline_escaped_quote_state.py`, `test_shell_bypass_denylist.py`, `test_execution_flag_detection.py`, `test_terminal_heredoc_background_guard.py`, `tests/cron/test_lifecycle_guard_heredoc_walk.py`
- file tools and search: `tests/tools/test_search_*.py` (11), `test_file_operations*.py` (3), `tests/security/test_gitspawn_config_injection.py`
- memory: `tests/tools/test_memory_tool*.py` (3)
- gateway: `tests/gateway/test_whatsapp_cloud.py`, `test_whatsapp_cloud_allowed_users.py`, `tests/hermes_cli/test_kanban_notify.py`, `test_curator_status.py`
- local runtime: `tests/hermes_cli/test_local_runtime*.py` (12), `test_local_preset_admission.py`
- config/secrets/core: `tests/test_hermes_constants.py`, `test_hermes_yaml.py`, `test_credential_file_permissions.py`, `tests/tools/test_tts_command_providers.py`, `test_transcription_command_providers.py`

**Baseline result (unmodified original tree):** 49 files — **1226 passed, 41 failed, 45 skipped, 5 errors**, 1659 s runner time (28 min wall, 4 workers). Every failure is host-specific to native Windows or to optional dependencies, none in code this release touches:

| Failing tests (baseline) | Cause |
|---|---|
| `test_whatsapp_cloud.py` webhook/health tests (15) | `aiohttp` is an optional extra not in the `dev`/`test` groups; `web` is `None` |
| `test_file_operations.py` umask/permission and symlink tests (6), `test_memory_tool.py` lock-permission tests (2) | POSIX permission semantics and symlink creation (WinError 1314: privilege required) on Windows |
| `test_search_zero_match_and_multipath.py` (6 failed, 5 errors), `test_search_auto_multiline.py` (1), `test_search_giant_line_containment.py` (3) | ripgrep not on `PATH` for the runner; symlinks need privilege; the grep lane cannot `stat` the pytest temp path through Git Bash |
| `test_approval.py` concurrent-coalescing and timeout tests (3) | Timing-sensitive tests on an overloaded host |
| `test_execution_flag_detection.py` real read-tool binaries (1) | Git Bash ships different GNU tool versions than CI |
| `test_lifecycle_guard_heredoc_walk.py` (2) | Windows path handling in the heredoc walk fixtures |
| `test_local_runtime_child_env.py` (1), `test_local_runtime_pm.py` (1) | Windows Job-object handle on a fake process; symlink privilege |

The project's CI workflows run these on Linux, macOS, and Windows runners with the right privileges and extras.

---

## Findings

| # | Finding | Severity | Status | Evidence / test |
|---|---|---|---|---|
| F1 | Heredoc bodies are lexed as shell by the approval floors: an unbalanced quote in a body hides every later command from the hardline blocklist, `approvals.deny`, and dangerous-pattern detection (original issue #140704) | High (unconditional floor bypass under `--yolo` / `mode: off`) | Fixed | `tests/tools/test_heredoc_floors.py`: 7 fail before, 10/10 pass after |
| F2 | `search_files` runs `git check-ignore` in a model-chosen root, executing that repo's `core.fsmonitor` program (original issue #137582) | High on POSIX (code execution before approval) | Fixed | `tests/tools/test_search_files_git_config_injection.py` |
| F3 | On native Windows the same gitignore filter never ran: native `git.exe` got the MSYS `/c/...` root and failed, so ignored directories leaked into results | Medium (wrong results; fixing it alone would make F2 exploitable on Windows) | Fixed | Same test file: 2 fail before; with the path fix but without the fsmonitor pin the marker file appears, proving the pin is load-bearing |
| F4 | Managed llama-server key in argv and in `llama-server.log` on every spawn (original issue #137804) | Medium (secret at rest and visible to local users) | Fixed | `tests/hermes_cli/test_local_runtime_api_key_secrecy.py`: 2 fail before, pass after |
| F5 | WhatsApp Cloud allowlist strips every non-digit, so distinct BSUIDs collide (original issue #138192) | High (authorization confusion, P1 in the original project) | Fixed | `tests/gateway/test_whatsapp_cloud_bsuid_allowlist.py`: 3 fail before, 4/4 pass after |
| F6 | Memory `patch` selects entries by folded typography but replaces only the raw text → "no-op" (original issue #138317) | Medium (memory edits silently impossible) | Fixed | `tests/tools/test_memory_patch_folding.py`: 4 fail before, 5/5 pass after |
| F7 | `/kanban` and `/curator` crash on an unclosed quote in messaging (original issue #140803) | Low (generic internal error instead of a reply) | Fixed | `tests/gateway/test_slash_command_unclosed_quote.py`: 2 fail before, pass after |
| F8 | `ls -1 <parent>` without `--` in the missing-path hint (reported in original issue #137582) | Low | Fixed in `search_files`; siblings in `tools/file_operations.py` left as is (see below) | Code review |
| F9 | Release, deploy, Docker Hub, R2, signing, paid-API workflows would run under the fork | High for a fork | Disabled | `.github/workflows-disabled/README.md` |
| F10 | Bug-report and setup issue forms required `hermes debug share`, which uploads config and logs to a public paste service | Low (privacy) | Changed to `--local`, optional, with a warning | `.github/ISSUE_TEMPLATE/` |
| F11 | `tts`/`stt` command-provider placeholder escaping on Windows (original issue #138361) | Medium | Not fixed (see below) | — |
| F12 | Memory reset/import bypass the store lock (original issue #140033) | Low–Medium | Not fixed (see below) | — |

---

## Improvements and verification

Each fix was proven by running its new test file through `scripts/run_tests.sh` against the original code (red) and the fixed code (green). For the files edited after the first red run, the original modules were temporarily copied back from the original clone, the test was run, and the fixed files were restored (checked with `diff -q`). Logs are kept in the agent's scratch folder (`regression-before-fix.log`, `regression-after-fix.log`, `regression-heredoc-before.log`, `regression-search-before.log`, `regression-search-after.log`, `regression-search-pathfix-only.log`).

### 1. Approval floors resume after a heredoc terminator (F1)

- **Change:** `tools/shell_heredoc.py` gains `blank_terminated_heredoc_bodies()`, a detection-only projection that turns every heredoc body ending at an exact terminator line into its newlines, reusing the module's existing quote-aware opener parser (`_scan_heredoc_command_unit`, `_find_heredoc_close`). `tools/approval_detection.py::_command_detection_variants` now yields the projections of the raw command and then of that blanked command (the old body is `_command_projection_variants`); `_deny_command_variants` and the execution-flag pass of `detect_dangerous_command` scan both sources too.
- **Why additive:** a shell (`bash <<EOF`) or unquoted-delimiter heredoc executes its body, so the raw command keeps being scanned; the blanked form only adds what the shell sees after the terminator. Commands without `<<` pay one substring check.
- **Evidence:** before — 7 of 10 tests fail (`cat <<'EOF' … it's done … EOF\nrm -rf /` returned `(False, None)`; `approvals.deny ["rm *"]` missed; `npm uninstall` after a heredoc was not flagged). After — 10/10 pass, including "benign command after a heredoc stays allowed" and "shell heredoc bodies are still scanned". The existing approval, hardline, deny, shell-bypass, and heredoc-guard suites were re-run (see [final run](#final-run)).

### 2. `search_files` git filter: no fsmonitor, and working on Windows (F2, F3, F8)

- **Change:** `tools/file_operations_search.py::_filter_gitignored_paths` runs `git -c core.fsmonitor=false -C <root> …` for both the `rev-parse` probe and `check-ignore --stdin`. On a local native Windows backend the root and the queried paths are passed in drive form (`_escape_native_tool_arg`, `_msys_to_windows_path`), the same convention the module already uses for `rg`. The missing-path hint lists with `ls -1 -- <parent>`.
- **Evidence:** the test builds a real repo whose `.git/config` sets `core.fsmonitor` to a marker-writing command, and asserts the payload is armed (plain `check-ignore` writes the marker). Before: 2 of 3 fail (on Windows, ignored directories are kept because git never ran). After: 3/3 pass. A third run with only the path fix (pin removed) fails with the marker file created, which shows the two changes must ship together.

### 3. llama-server key out of argv and logs (F4)

- **Change:** `hermes_cli/local_runtime/supervisor.py::_api_key_args` passes `--api-key-file <runtimes>/.api_key` when that persisted file holds exactly the key (`_stable_api_key` already writes it), and falls back to `--api-key` only when it cannot. The `# spawn:` line written to `llama-server.log` masks the key in either case.
- **Compatibility:** `--api-key-file` predates llama.cpp's router mode, which the supervisor requires. `recovery.legacy_recorded_process` still matches `--api-key` in argv, which is correct: it only applies to legacy state records written by older versions that launched with the argv form.
- **Evidence:** before, both tests fail (key in argv; key in the log). After, both pass, and the existing local-runtime suites (load mode, child env, recovery, presets) pass as in the baseline.

### 4. WhatsApp Cloud BSUIDs compared exactly (F5)

- **Change:** `plugins/platforms/whatsapp_cloud/adapter.py` normalizes an id to digits only when it is phone-shaped (`^\+?[\d\s().\-]+$`, after dropping an `@…` JID suffix); any other id (a BSUID such as `DE.1A2B3C4D5E`, `*`) is kept byte for byte. The same normalizer is applied to allowlist entries and to the sender.
- **Evidence:** before, `DE.12345ABCDE` was admitted by an allowlist containing `DE.1A2B3C4D5E`, a BSUID matched the phone entry `12345`, and case was ignored (3 failures). After, 4/4 pass; formatted phone entries (`+1 (555) 123-4567`, `…@s.whatsapp.net`) still match, and the existing `TestAllowlistNormalization` contract holds.

### 5. Memory `patch` through typography folding (F6)

- **Change:** `tools/memory_tool_store.py::_folded_spans` folds the entry character by character with the same rules as `_normalize_for_match` (quotes, dashes, whitespace runs, literal `\n`), keeping each folded character's source span, so a folded match maps back to the exact original text. `_patch_entry` uses that span when `old_text` is not literally present, and still refuses a span that occurs more than once. Single patches, atomic batches, and approved staged writes share `_patch_entry`.
- **Evidence:** before, curly-quote/em-dash, re-wrapped-line, and batch patches failed as "Patch is a no-op" (4 failures). After, 5/5 pass, and `tests/tools/test_memory_tool.py` is unchanged from the baseline.

### 6. `/kanban` and `/curator` unclosed quotes (F7)

- **Change:** `gateway/slash_commands.py` catches the `ValueError` from `shlex.split` in both handlers and replies with the existing localized error strings (`gateway.kanban.error_prefix`, `cli.commands.curator.failed`), the same shape `/resume` already uses. No new locale keys.
- **Evidence:** before, both tests raise `ValueError: No closing quotation`; after, both replies name the problem.

### Final run

The baseline subset plus the 6 new test files and the workflow contract tests that now read through `tests/ci/workflow_files.py` were run with the same command (`final-subset.txt`, 68 files):

**Final result:** 68 files — **1352 passed, 44 failed, 92 skipped, 5 errors**, 2535 s runner time (42.5 min wall on a heavily shared host).

| Compared with the baseline (same 49 files) | Result |
|---|---|
| Baseline failures still failing | 38 of 41, same tests, same host causes |
| Baseline failures now passing | 3 (`test_approval.py` coalescing/timeout timing tests; flaky under load) |
| New regression tests (6 files, 26 tests) | All pass |
| `test_local_runtime_processes.py` (3 failures in the final run) | Real Windows process-tree tests that never import the changed supervisor; re-run alone: 8/8 pass |
| Workflow contract and layout tests (13 files: the ones now reading via `workflow_files.py`, the workflow-glob checks, `test_plugin_validate_action.py` — POSIX-only, skipped here — and `tests/test_tests_tree_layout.py`) | All pass except 3 tests that also fail with the workflows copied back to `.github/workflows/` (the original layout): they shell out to `bash`, which resolves to the WSL stub without a distribution on this host, or read Windows package metadata (`KeyError: 'Executable'`) |

No test, assertion, or lint rule was skipped, weakened, or removed.

**Lint and types on changed files:** `ruff check` on every changed Python file passes (project `ruff.toml`). `ty check` on the changed modules reports only diagnostic kinds already present in the original code (mixin attributes unresolved on `Self`, `set[Never]` inference); none is new in the changed lines.

---

## Rebrand and fork safety

- **Renamed (identity):** README title, banner (`docs/assets/cavaleiro-banner.svg`), badges, clone URLs, issue/PR/security links in the README, `CONTRIBUTING.md`, `SECURITY.md`, issue forms, PR template, and the `plugin-validate` composite action's fetch URL.
- **Kept (identifiers):** the `hermes`, `hermes-agent`, and `hermes-acp` commands; the `hermes-agent` distribution and version scheme; import paths; `~/.hermes` and `%LOCALAPPDATA%\hermes`; `HERMES_*` variables; config keys; plugin, skill, toolset, and slash-command IDs; protocol identifiers; the updater's notion of the original project's remote; the opt-in telemetry endpoint (off by default, documented in the README's Compatibility section).
- **License:** MIT text and the original copyright line verbatim, plus the derivative notice and `Copyright (c) 2026 Cavaleiro AI (modifications in Cavaleiro Learning Agent)`.
- **Translations:** the original project's `README.{es,zh-CN,ur-pk}.md`, `CONTRIBUTING.es.md`, and `SECURITY.es.md` moved to `docs/original-i18n/` with a note and rebased links.
- **Workflows:** 21 workflows moved to `.github/workflows-disabled/` (release, canary, desktop bundles and signing, Docker Hub, R2 archives, Termux, docs deploy and monitor, skills index, JS autofix, live provider canaries, installer E2E against the original project's assets, and the PR comment bot). The other 36 workflows (build, test, lint, and repository checks) remain with unchanged action pins. The workflow contract tests resolve files through `tests/ci/workflow_files.py` so the disabled release workflows keep their coverage; no assertion changed.
- **CODEOWNERS** is `* @cavaleiro-ai`. There was no `FUNDING.yml`. Dependabot (GitHub Actions only) is kept.
- **Identity cleanup:** the public files (README, contributing guide, security policy, code of conduct, issue forms, PR template, package metadata, this folder) name only Cavaleiro AI; the README credits the original project in one line under **License**. Issue numbers of the original project are cited as plain text.

---

## Not done, and why

- **`website/` is renamed but not deployed.** The Docusaurus sources use the product name Cavaleiro Learning Agent, and their repository, issue, security, and community links point to this repository; its deploy workflow is disabled. Per-skill pages and catalogs generated from `SKILL.md` keep the skills' own text (the generator's repository link and catalog title were updated), the user-stories page keeps third-party testimonials about the original project, and functional URLs (installers, Nous Portal, release assets, model catalog, issue and pull request numbers cited as evidence) still point to the original project's services.
- **TTS/STT command-provider escaping on Windows (F11, original issue #138361).** A correct fix needs argv execution without `cmd.exe` or a full cmd-escaping scheme and real Windows reproduction; a partial fix would risk false safety. Left for a dedicated change.
- **Memory reset/import locking (F12, original issue #140033).** Needs a conditional-publish contract and cross-process tests of dashboard and CLI resets; larger than this release's scope.
- **`ls -1` without `--` in `tools/file_operations.py`.** Adding `--` there changes the exact command string asserted by `tests/tools/test_file_ops_single_roundtrip.py`; it was left for a change that updates that contract test deliberately.
- **Heredoc false positives.** The fix closes the bypass direction of original issue #140704. Body lines that look like denied commands can still be blocked (the pre-existing, conservative behavior).
- **Full test suite and JS/Rust suites** were not run on this host (time per file; see [Baseline](#baseline)). The project's CI workflows cover them.
- **`python scripts/check`** (code-health ratchet) needs `origin/main` history, which the fresh repository does not have; complexity of the new functions was kept well under the documented caps (CC ≤ 20, ≤ 300 lines, nesting ≤ 6) and no touched file approaches 2,000 lines.
- **Runner labels** were swapped to GitHub-hosted runners after the initial run, at the owner's request (see the CHANGELOG). Verification: all 36 kept workflows parse as YAML, and `pytest tests/ci` gives 622 passed, 7 failed, 53 skipped. The same 7 tests fail identically with the pre-swap workflows restored, so the swap introduced no failure; they depend on git history, the WSL `bash` stub, and signing tools absent on this host.

## Known limitations

- Kept workflows now use GitHub-hosted runners (see the runner swap above). Jobs sized for the original project's 32-vCPU Blacksmith machines run slower on standard hosted runners, and `windows-11-arm` depends on GitHub's free ARM runners for public repositories.
- `hermes update` in a git checkout pulls from `origin` and may offer to add the original project's remote.
- The one-line installers, the desktop app's auto-update channel, Nous Portal, Tool Gateway, Skills Hub, and opt-in telemetry are services of the original project.
- On Windows, the `find`-only fallback of `search_files(target="files")` (used when ripgrep is missing) does not apply gitignore filtering to plain files, as in the original project.

## Recommended next steps

1. Get `ci.yaml` green on the repository; its runner labels already point to GitHub-hosted runners.
2. Fix original issue #138361 (command-provider escaping) with argv execution on Windows and Windows-hosted tests.
3. Route memory reset and import through the store lock (original issue #140033).
4. Decide whether to publish the Docker image and desktop bundles under Cavaleiro credentials; re-enable the matching workflows as described in their README.
5. Deploy the `website/` documentation under a Cavaleiro domain, and decide whether to keep the user-stories page.
6. Offer F1–F7 to the original project as pull requests that cite the issues above.

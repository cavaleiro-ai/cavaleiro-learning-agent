# Changelog

All notable changes to Cavaleiro Learning Agent are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use [Semantic Versioning](https://semver.org/).

The original project does not keep a changelog file. This file covers only what Cavaleiro Learning Agent changes on top of the original project.

## [Unreleased]

### Changed

- Identity cleanup: the README, contributing guide, security policy, code of conduct, issue forms, pull request template, CODEOWNERS, package metadata, and `docs/cavaleiro/` refer only to Cavaleiro AI, and the README credits the original project in one line under **License**. Issue numbers of the original project are cited as plain text.
- The inherited manuals (`website/` Docusaurus sources, `docs/original-i18n/`, `AGENTS.md`) use the product name Cavaleiro Learning Agent, and their community, issue, and security contacts point to this repository. Service names (Nous Portal, the Hermes model family) and functional URLs are unchanged.
- Removed the original project's contributor data — 2,054 email-mapping files under `contributors/emails/`, `contributors/reattributed.tsv`, and `.mailmap` — and emptied `LEGACY_AUTHOR_MAP`. This repository carries none of that commit history. Two contributor-map tests now use example data and still cover the same rules.

## Cavaleiro Learning Agent 1.0.0 — 2026-10-17

First release of Cavaleiro Learning Agent, based on the original project's commit `e6cf2a9b1e8f98d40408b09a9a55993c8459b4b4` (2026-10-17). Every fix below has a regression test that fails on the original code and passes here; the runs are recorded in the [engineering report](docs/cavaleiro/ENGINEERING.md).

### Security

- **Heredoc bodies no longer hide commands from the approval floors.** The shell lexer behind the hardline blocklist, `approvals.deny`, and the dangerous-command detector had no heredoc model, so an unbalanced quote inside a body (`it's done`) opened a quote that never closed and every later line became invisible: `rm -rf /` on the line after the terminator ran under `approvals.mode: off` or `--yolo`. The floors now also scan a projection of the command with each terminated heredoc body blanked (`tools/shell_heredoc.py::blank_terminated_heredoc_bodies`), in addition to the raw command, so bodies that a shell executes are still checked. Test: `tests/tools/test_heredoc_floors.py`. Original issue #140704.
- **`search_files` no longer runs the searched repository's `core.fsmonitor` program.** Its gitignore filter ran `git check-ignore` in the model-chosen search root, and `check-ignore` reads the index, which executes a repo-configured fsmonitor command as the user before any approval. Both git calls now pin `core.fsmonitor=false`. Test: `tests/tools/test_search_files_git_config_injection.py`. Original issue #137582.
- **The managed llama.cpp server key no longer leaks through argv and `llama-server.log`.** The supervisor passed the key as `--api-key <value>` (readable by every local user through the process list) and wrote the whole command line, key included, to `llama-server.log` on every spawn and crash-restart, outside the redacting log formatter. It now passes the persisted key file with `--api-key-file`; the argv form remains only when the key file cannot hold the key, and the spawn log line masks the key either way. Test: `tests/hermes_cli/test_local_runtime_api_key_secrecy.py`. Original issue #137804.
- **WhatsApp Cloud allowlists compare business-scoped user ids (BSUIDs) exactly.** Normalization stripped every non-digit from entries and senders, so two different BSUIDs with the same digits (`DE.1A2B3C4D5E` and `DE.12345ABCDE`) admitted each other, and a BSUID could match a phone entry. Only phone-shaped ids are reduced to digits now. Test: `tests/gateway/test_whatsapp_cloud_bsuid_allowlist.py`. Original issue #138192.

### Fixed

- **`search_files` gitignore filtering works on native Windows.** The filter handed the root to the native `git.exe` in the Git Bash `/c/...` form, which it cannot read because the agent disables MSYS argument conversion; git failed and every gitignored directory leaked into `target="files"` results. Root and queried paths now use the drive form there (found while reproducing original issue #137582; the fsmonitor pin above is what keeps this from turning the leak into code execution on Windows).
- **The memory tool's `patch` edits entries it selected through typography folding.** Entry selection already matched retyped quotes, dashes, and re-wrapped lines, but `patch` then replaced only the raw `old_text`, which is not in the entry, and failed as "Patch is a no-op" in single calls, atomic batches, and approved staged writes. It now splices the span the folded text matched and still refuses a span that occurs more than once. Test: `tests/tools/test_memory_patch_folding.py`. Original issue #138317.
- **`/kanban` and `/curator` in messaging apps answer an unclosed quote with a named error.** `shlex.split` raised `ValueError: No closing quotation` out of both handlers (`/kanban show it's`), so users got the generic internal-error reply. Test: `tests/gateway/test_slash_command_unclosed_quote.py`. Original issue #140803.
- The missing-path hint in `search_files` lists the parent directory with `ls -1 --`, so a directory named like an option (`-R`) is read as an operand (reported alongside original issue #137582).
- `CONTRIBUTING.md` linked the "Don't fake the host OS" rules to the root `AGENTS.md`, where that section does not exist; it now points to `tests/AGENTS.md`.

### Added

- `README.md` rebranded for Cavaleiro Learning Agent, with **What Cavaleiro Learning Agent adds**, **Compatibility**, and **License** sections, and a full Portuguese version in `README.pt-BR.md`.
- `docs/cavaleiro/GUIA-PT-BR.md`: a complete Portuguese guide (what it is, architecture, installation on Windows/macOS/Linux, first steps, examples, configuration, troubleshooting, contributing).
- `docs/cavaleiro/ENGINEERING.md`: architecture map, test baseline, findings table, verification of every fix, limitations, and next steps.
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), bug and feature issue forms, and a pull request template for this repository.
- `.github/workflows-disabled/README.md`, explaining which workflows were disabled and how to re-enable them.

### Changed

- Project identity: Cavaleiro Learning Agent, with repository links in the README, contributing guide, security policy, issue forms, and pull request template pointing to `https://github.com/cavaleiro-ai/cavaleiro-learning-agent`. Code identifiers are unchanged: the `hermes` command, the `hermes-agent` distribution, import paths, `~/.hermes`, environment variables, and plugin and skill IDs (see [Compatibility](README.md#compatibility)).
- `LICENSE` keeps the MIT text and the original copyright line verbatim and adds the derivative-work notice and the Cavaleiro AI copyright line for the modifications.
- `CONTRIBUTING.md` and `SECURITY.md` are adapted for this repository.
- The original project's translated READMEs (Español, 中文, اردو) and the Spanish contributing guide and security policy moved to `docs/original-i18n/`, with a note and rebased links.
- `.github/CODEOWNERS` now assigns `* @cavaleiro-ai`.
- Workflows that publish, sign, deploy, call paid model APIs, use the original project's credentials, or probe its infrastructure moved to `.github/workflows-disabled/` ([why and how to re-enable](.github/workflows-disabled/README.md)): `archive-inputs`, `bootstrap-installer-build`, `canary-release`, `ci-review-comment`, `deploy-site`, `desktop-bundled-release`, `docker`, `docs-search-monitor`, `install-e2e` (with `install-e2e-run`, `install-e2e-macos-run`, `install-e2e-windows-run`, `install-e2e-red`), `js-autofix`, `live-providers`, `sandbox-image`, `skills-index`, `skills-index-freshness`, `stable-release`, `stable-release-publication`, and `termux-verify`. Build, test, and lint workflows stay in place with their action pins unchanged.
- The workflow contract tests under `tests/ci/` and `tests/scripts/` read a workflow through `tests/ci/workflow_files.py`, which looks in `.github/workflows/` and then `.github/workflows-disabled/`, so the disabled release workflows keep their test coverage. Assertions are unchanged.
- The `plugin-validate` composite action fetches from this repository instead of the original project's (its test's URL rewrite follows).
- Kept workflows run on GitHub-hosted runners instead of the original project's Blacksmith and org-configured larger runners: `blacksmith-*-ubuntu-2404` → `ubuntu-24.04`, `blacksmith-*-windows-2025` → `windows-2025`, `blacksmith-12vcpu-macos-latest` → `macos-latest`, and `windows-latest-32-arm-core` → `windows-11-arm`. Without this, those jobs would wait for a runner forever in this repository.

[Unreleased]: https://github.com/cavaleiro-ai/cavaleiro-learning-agent/compare/v1.0.0...HEAD

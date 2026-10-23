**English** · [Português (Brasil)](README.pt-BR.md)

<a id="top"></a>

<p align="center">
  <img src="docs/assets/cavaleiro-banner.svg" alt="Cavaleiro Learning Agent — an agent that learns and grows with you." width="100%">
</p>

# Cavaleiro Learning Agent

**A self-improving personal AI agent: it learns from experience, remembers across sessions, and runs where you work.**

<p align="center">
  <a href=".github/workflows/ci.yaml"><img src="https://github.com/cavaleiro-ai/cavaleiro-learning-agent/actions/workflows/ci.yaml/badge.svg" alt="CI status on GitHub Actions" /></a>
  &nbsp;
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="License: MIT" /></a>
  &nbsp;
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/release-1.0.0-e7ba7d" alt="Release 1.0.0" /></a>
</p>

Cavaleiro Learning Agent is maintained by [Cavaleiro AI](https://github.com/cavaleiro-ai). It keeps every feature of the original project (see [License](#license)) and adds security and reliability fixes, each proven by a regression test (see [What Cavaleiro Learning Agent adds](#what-cavaleiro-learning-agent-adds)).

The agent has a built-in learning loop: it creates skills from experience, improves them while using them, keeps curated memory, searches its own past conversations, and builds a model of who you are across sessions. Run it on a small VPS, a GPU box, or serverless infrastructure, and talk to it from a terminal or from Telegram, Discord, Slack, WhatsApp, Signal, and more.

Use the model you want: Nous Portal, OpenRouter, OpenAI, Anthropic, a local llama.cpp server, your own endpoint, and many others. Switch with `hermes model`, with no code changes.

<table>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, email, and the CLI, all from one gateway process. Voice memo transcription and cross-platform conversation continuity.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks, and skills that improve during use. FTS5 session search with LLM summarization for cross-session recall. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform: daily reports, nightly backups, weekly audits, written in natural language and run unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Isolated subagents for parallel workstreams, and Python scripts that call tools over RPC.</td></tr>
<tr><td><b>Runs anywhere</b></td><td>Seven terminal backends: local, Docker, SSH, Singularity, Modal, Daytona, and Vercel Sandbox.</td></tr>
<tr><td><b>Guarded tool execution</b></td><td>Dangerous-command detection, an unconditional hardline blocklist, your own <code>approvals.deny</code> rules, DM pairing, and container isolation.</td></tr>
</table>

---

## Install

This repository installs from source. The commands, configuration files, and data directory are the same as the original project's (see [Compatibility](#compatibility)).

> The original project's one-line installers install the original project, not this repository. Install from source as shown below.

**Requirements:** Git (with `git-lfs`), and a network connection for the first setup. The setup script stages its own pinned `uv` and Python 3.14; you do not need to install Python yourself.

### Linux, macOS, WSL2

```bash
git clone https://github.com/cavaleiro-ai/cavaleiro-learning-agent.git
cd cavaleiro-learning-agent
./setup-hermes.sh          # stages uv + Python 3.14 and the locked dependencies
source ./activate          # puts `hermes` for this checkout on your shell
hermes setup               # pick a provider, model, and tools
hermes                     # start chatting
```

### Windows (native, PowerShell)

```powershell
git clone https://github.com/cavaleiro-ai/cavaleiro-learning-agent.git
cd cavaleiro-learning-agent
.\setup-hermes.ps1
. .\activate.ps1           # the leading dot and space are required
hermes setup
hermes
```

Run `deactivate` to leave the environment. To keep experiments away from your real data, set `HERMES_HOME` to a separate folder before the first `hermes setup`. The [Portuguese guide](docs/cavaleiro/GUIA-PT-BR.md) walks through every step on Windows, macOS, and Linux, including troubleshooting.

### Windows Defender flags `uv.exe`

Some antivirus engines quarantine `uv.exe`, Astral's Rust package manager that the setup stages to manage Python. This is a known false positive for unsigned Rust binaries. Verify the binary against Astral's release attestation (`gh attestation verify <zip> --repo astral-sh/uv`) and, if it matches, exclude the folder (not the file hash, which changes with every `uv` release). See [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553).

---

## Getting started

```bash
hermes              # Interactive CLI: start a conversation
hermes model        # Choose your LLM provider and model
hermes tools        # Configure which tools are enabled
hermes config set   # Set individual config values
hermes config get   # Print individual config values
hermes gateway      # Start the messaging gateway (Telegram, Discord, etc.)
hermes setup        # Run the full setup wizard
hermes doctor       # Diagnose problems
```

### CLI and messaging quick reference

Start the terminal UI with `hermes`, or run the gateway and talk to the agent from a messaging app. Many slash commands work in both.

| Action | CLI | Messaging platforms |
|---|---|---|
| Start chatting | `hermes` | `hermes gateway setup` + `hermes gateway start`, then message the bot |
| Start a fresh conversation | `/new` or `/reset` | `/new` or `/reset` |
| Change model | `/model [provider:model]` | `/model [provider:model]` |
| Set a personality | `/personality [name]` | `/personality [name]` |
| Retry or undo the last turn | `/retry`, `/undo` | `/retry`, `/undo` |
| Compress context or check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]` |
| Browse skills | `/skills` or `/<skill-name>` | `/<skill-name>` |
| Interrupt current work | `Ctrl+C` or send a new message | `/stop` or send a new message |

### Where your data lives

| Path | Purpose |
|---|---|
| `~/.hermes/config.yaml` | Settings: model, terminal backend, toolsets, approvals, compression |
| `~/.hermes/.env` | API keys and other secrets only |
| `~/.hermes/memories/` | Persistent memory (`MEMORY.md`, `USER.md`) |
| `~/.hermes/skills/` | Bundled, hub-installed, and agent-created skills |
| `~/.hermes/state.db` | SQLite session database with full-text search |
| `~/.hermes/cron/` | Scheduled jobs |

On native Windows the default home is `%LOCALAPPDATA%\hermes`. `HERMES_HOME` overrides it, and profiles get their own homes.

### Safety controls worth knowing

- `approvals.mode` in `config.yaml` (`manual`, `smart`, or `off`) decides when a risky terminal command needs your approval. The hardline blocklist and your `approvals.deny` globs apply even in `off` mode and under `--yolo`.
- The terminal backend decides where commands run. `local` runs on your machine as your user; `docker`, `ssh`, `modal`, `daytona`, `singularity`, and `vercel` isolate execution.
- Messaging platforms only answer allowlisted or paired users. Keep allowlists narrow.

---

## Documentation

| Document | What it covers |
|---|---|
| [Guia em português](docs/cavaleiro/GUIA-PT-BR.md) | What the agent is, architecture, step-by-step install on Windows/macOS/Linux, first steps, configuration, troubleshooting, contributing |
| [Engineering report](docs/cavaleiro/ENGINEERING.md) | Architecture map, test baseline, every finding and fix with its evidence, known limitations |
| [Changelog](CHANGELOG.md) | What changed in each Cavaleiro release |
| [`website/docs/`](website/docs/) | The full user and developer documentation (Docusaurus sources), which applies command for command |
| [AGENTS.md](AGENTS.md) | The development guide for people and coding agents working in this tree |

---

## What Cavaleiro Learning Agent adds

Everything from the original project, plus fixes that each come with a regression test that fails on the original code and passes here. Details and evidence are in the [changelog](CHANGELOG.md#cavaleiro-learning-agent-100--2026-10-17) and the [engineering report](docs/cavaleiro/ENGINEERING.md).

- **Heredoc bodies no longer hide commands from the approval floors.** An apostrophe inside a heredoc body (`it's done`) used to make the hardline blocklist, `approvals.deny`, and the dangerous-command detector miss the command after the heredoc, so `rm -rf /` ran under `--yolo`.
- **`search_files` no longer runs a searched repository's `core.fsmonitor` program,** and its gitignore filter works on native Windows instead of silently listing ignored directories.
- **The local llama.cpp server key stays out of the process list and `llama-server.log`.** It is passed with `--api-key-file`, and the spawn log masks it.
- **WhatsApp Cloud allowlists compare business-scoped user ids exactly,** so two different ids with the same digits no longer admit each other.
- **The memory tool's `patch` edits entries matched through retyped quotes, dashes, or line wraps** instead of failing as a no-op.
- **`/kanban` and `/curator` in messaging apps answer an unclosed quote with a clear error** instead of the generic internal-error reply.
- **Fork-safe repository:** publishing, signing, deploy, and paid-API workflows are disabled until you configure your own credentials ([why and how](.github/workflows-disabled/README.md)), plus issue forms, a pull request template, a code of conduct, and a Portuguese README and guide.

## Compatibility

Cavaleiro Learning Agent renames the **project**, not the **interfaces**, so existing setups, scripts, and integrations keep working:

- The command is still **`hermes`** (also `hermes-agent` and `hermes-acp`), and the Python distribution is still **`hermes-agent`**. Import paths (`agent`, `tools`, `gateway`, `hermes_cli`, …) are unchanged.
- The data directory is still `~/.hermes` (`%LOCALAPPDATA%\hermes` on native Windows), with the same `config.yaml`, `.env`, `state.db`, memory, skill, and cron formats. A home created by the original project works as is, and so do profiles.
- Environment variables (`HERMES_HOME`, `HERMES_*`, provider keys), slash commands, plugin and skill IDs, toolset names, and the ACP/MCP/JSON-RPC protocols are unchanged.
- **Updates:** in a git checkout, `hermes update` pulls from your `origin` remote (this repository). It may offer to add the original project's repository as a remote; decline if you want to stay on Cavaleiro releases.
- **Telemetry** stays off by default. The optional shared-metrics upload (`telemetry.shared_metrics`, two separate opt-ins) still points at the original project's endpoint; it was not repointed. Passive update checks (`updates.check`) and the Nous Portal, Tool Gateway, and Skills Hub integrations talk to the original project's services when you use them.
- In-product strings and artwork, including the desktop app's names, are unchanged from the original project.

## Contributing

Contributions are welcome. Read the [contributing guide](CONTRIBUTING.md) for the development setup, the test runner, and the pull request process, and follow the [code of conduct](CODE_OF_CONDUCT.md). Report vulnerabilities privately as described in the [security policy](SECURITY.md).

[Report a bug](https://github.com/cavaleiro-ai/cavaleiro-learning-agent/issues/new/choose) · [Suggest an improvement](https://github.com/cavaleiro-ai/cavaleiro-learning-agent/issues/new/choose) · [Changelog](CHANGELOG.md)

The original project's translations (Español, 中文, اردو) are kept in [docs/original-i18n](docs/original-i18n/README.md).

## License

Based on Hermes Agent · MIT License · see [LICENSE](LICENSE). Not affiliated with the original project.

<p align="center"><a href="#top">Back to top ↑</a></p>

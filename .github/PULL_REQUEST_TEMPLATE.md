## What does this PR do?

<!-- Describe the change clearly. What problem does it solve? Why is this approach the right one? -->



## Related Issue

<!-- Link the issue this PR addresses. If no issue exists, consider creating one first. If the fix comes from an issue of the original project, cite its number as plain text. -->

Fixes #

## Type of Change

<!-- Check the one that applies. -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix (undisclosed vulnerabilities in [SECURITY.md](../SECURITY.md) §3.1 scope go to [Security Advisories](https://github.com/cavaleiro-ai/cavaleiro-learning-agent/security/advisories/new) first, not a public PR)
- [ ] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

<!-- List the specific changes. Include file paths for code changes. -->

-

## How to Test

<!-- Steps to verify this change works. For bugs: reproduction steps + proof that the fix works (the regression test failing before and passing after). -->

1.
2.
3.

## Checklist

<!-- Complete these before requesting review. Tick only what you actually ran. -->

### Code

- [ ] I've read the [Contributing Guide](../CONTRIBUTING.md)
- [ ] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [ ] I searched for [existing PRs](https://github.com/cavaleiro-ai/cavaleiro-learning-agent/pulls) to make sure this isn't a duplicate
- [ ] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I ran the relevant tests with `scripts/run_tests.sh <paths>` (never bare `pytest`) and they pass
- [ ] `python scripts/check` passes (the blocking lint and code-health checks CI runs)
- [ ] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [ ] I've tested on my platform: <!-- e.g. Ubuntu 24.04, macOS 15.2, Windows 11 -->

### Documentation & Housekeeping

<!-- Check all that apply. It's OK to check "N/A" if a category doesn't apply to your change. -->

- [ ] I've added a line under **Unreleased** in [CHANGELOG.md](../CHANGELOG.md) — or N/A
- [ ] I've updated relevant documentation (README, `README.pt-BR.md`, `docs/`, docstrings) — or N/A
- [ ] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [ ] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [ ] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](../CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [ ] I've updated tool descriptions/schemas if I changed tool behavior — or N/A
- [ ] No secrets, tokens, private URLs, or personal settings were added

## For New Skills

<!-- Only fill this out if you're adding a skill. Delete this section otherwise. -->

- [ ] This skill is **broadly useful** to most users (if bundled) — see [Contributing Guide](../CONTRIBUTING.md#should-the-skill-be-bundled)
- [ ] SKILL.md follows the [standard format](../CONTRIBUTING.md#skillmd-format) (frontmatter, trigger conditions, steps, pitfalls)
- [ ] No external dependencies that aren't already available (prefer stdlib, curl, existing Hermes tools)
- [ ] I've tested the skill end-to-end: `hermes --toolsets skills -q "Use the X skill to do Y"`

## Screenshots / Logs

<!-- If applicable, add screenshots or log output showing the fix/feature in action. -->

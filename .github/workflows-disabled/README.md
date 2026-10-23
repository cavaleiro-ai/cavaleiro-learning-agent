# Disabled workflows

GitHub Actions only runs workflow files in `.github/workflows/`. The files in this folder came from the original project and were moved here when Cavaleiro Learning Agent was created, so that nothing in this repository publishes, signs, deploys, or calls paid services under the original project's identity or with its credentials.

They are kept unchanged so their logic stays reviewable and their contract tests keep running: `tests/ci/workflow_files.py` resolves a workflow from `workflows/` first and from this folder second.

## What is here and why

| Workflow | Why it is disabled |
|---|---|
| `stable-release.yml`, `stable-release-publication.yml` | Cut and publish stable releases: GitHub releases and tags, Docker Hub images, Cloudflare R2 channels, Microsoft Store submission. Needs `DOCKERHUB_*`, `CLOUDFLARE_R2_*`, `MS_STORE_*` secrets. |
| `canary-release.yml` | Scheduled canary releases: pushes tags, creates and prunes releases, uploads to Cloudflare R2. |
| `desktop-bundled-release.yml` | Builds, signs, and notarizes desktop bundles (Apple and Windows code-signing certificates), signs the Termux APT repository with GPG, uploads to R2 and the Microsoft Store. |
| `bootstrap-installer-build.yml` | Builds and signs the bootstrap installer with Apple and Windows signing credentials. |
| `archive-inputs.yml` | Archives release inputs to Cloudflare R2. |
| `termux-verify.yml` | Verifies the Termux package against the R2-hosted repository; needs `CLOUDFLARE_R2_*`. |
| `docker.yml`, `sandbox-image.yml` | Build and push images to Docker Hub under the original project's namespace (`DOCKERHUB_*` secrets). |
| `deploy-site.yml` | Deploys the documentation site (GitHub Pages and a Vercel deploy hook) with a GitHub App key. |
| `docs-search-monitor.yml` | Probes search on the original project's production documentation site. |
| `skills-index.yml`, `skills-index-freshness.yml` | Rebuild and publish the skills index with a GitHub App key and open issues as the original project's bot. |
| `js-autofix.yml` | Pushes autofix commits and opens auto-merging pull requests with a GitHub App key. |
| `live-providers.yml` | Calls real, paid model APIs (Anthropic, OpenAI, OpenRouter, Gemini, xAI, Nous) with live API keys. |
| `install-e2e.yml`, `install-e2e-run.yml`, `install-e2e-macos-run.yml`, `install-e2e-windows-run.yml`, `install-e2e-red.yml` | Release verification of the published installers: they download the original project's release assets by default, and `install-e2e-red.yml` files tracking issues on failure. |
| `ci-review-comment.yml` | A write-token bot that comments CI results on pull requests and waits for the Docker workflow above, which no longer runs here. |

## What still runs

Build, test, and lint workflows stay in `.github/workflows/` and need nothing beyond the automatic `GITHUB_TOKEN`: `ci.yaml` and the reusable workflows it calls (`tests.yml`, `tests-os.yml`, `lint.yml`, `js-tests.yml`, `rust-tests.yml`, the desktop E2E suites, and the repository checks), plus `nix.yml`, `osv-scanner.yml`, `plugin-catalog-ci.yml`, `pm-bundle.yml`, `desktop-bundle-smoke.yml`, `label-rerun.yml`, and the Windows E2E lanes. Their action pins are unchanged.

The original project runs them on [Blacksmith](https://www.blacksmith.sh/) runners and on org-configured larger runners. In this repository the kept workflows already use GitHub-hosted runners: `blacksmith-*-ubuntu-2404` → `ubuntu-24.04`, `blacksmith-*-windows-2025` → `windows-2025`, `blacksmith-12vcpu-macos-latest` → `macos-latest`, and `windows-latest-32-arm-core` → `windows-11-arm`. Swap the labels the same way in any workflow you re-enable from this folder. The pinned `useblacksmith/checkout` action also works on GitHub-hosted runners.

## How to re-enable a workflow

1. Read the workflow and decide where it should publish: your own Docker Hub namespace, your own R2 bucket and public base URL, your own signing certificates, your own site. Replace every name, URL, bucket, and namespace of the original project in it.
2. Create the secrets it reads under **Settings → Secrets and variables → Actions** of this repository (or an environment with required reviewers for release jobs). Never reuse the original project's credentials.
3. Move the file back with `git mv .github/workflows-disabled/<name>.yml .github/workflows/`. Move workflows that call each other together: `stable-release.yml` calls `desktop-bundled-release.yml`, `docker.yml`, `termux-verify.yml`, and the `install-e2e*` family; `install-e2e.yml` calls the three `install-e2e-*-run.yml` files.
4. Run it once with `workflow_dispatch` on a branch, and check every upload target before letting it run on a schedule or on tags.
5. Note the change in the [changelog](../../CHANGELOG.md).

# Release Publishing

This page documents the repository-owned PyPI release path for Houmao.

## Workflow Contract

Public package publication is handled by the GitHub Actions workflow `.github/workflows/pypi-release.yml`.

The workflow contract is:

- Trigger: GitHub `release.published`
- Source branch expectation: the release is cut from `main`
- Build behavior: build both wheel and sdist from the published tag
- Validation: run `twine check` on the exact built artifacts
- Publish behavior: publish the downloaded build artifacts to PyPI
- Docs publication: publishing a GitHub release also triggers the docs workflow to build from the same tag and deploy GitHub Pages
- System-skills publication: every release publishes the root-level skill collection to the matching Git tag in `igamenovoer/houmao-skills`; stable releases also advance its `main` branch, while prereleases leave `main` unchanged
- Authentication: GitHub OIDC trusted publishing, using the GitHub environment `pypi`

Because the workflow is release-driven, the workflow file must already exist on `main` before maintainers publish a release.

## Trusted Publisher Setup

Configure PyPI trusted publishing before creating a release.

### GitHub Repository Setup

Create a GitHub environment named `pypi`.

No repository secret is required for the default publication path. The publish job uses the workflow's OIDC token and `pypa/gh-action-pypi-publish`.

System-skill publication uses a separate `HOUMAO_SKILLS_DEPLOY_KEY` repository secret. Its public key must be configured as a write-enabled deploy key on `igamenovoer/houmao-skills`. The private key is scoped to that repository and lets `.github/workflows/sync-houmao-skills.yml` publish the released skill tree and matching immutable tag without a cross-repository personal access token.

### System-Skills Repository Setup and Maintenance

`igamenovoer/houmao-skills` is a generated release mirror. Keep each released `houmao-*` skill directory at repository root so `npx skills add https://github.com/igamenovoer/houmao-skills` discovers the collection directly. Do not add a wrapping `houmao/`, `skills/`, `public/`, or version directory, and do not compose or rewrite skill content in the mirror. Source changes belong under `src/houmao/agents/assets/system_skills/public/` in this repository.

The release workflow copies the complete public directories, removes obsolete root-level `houmao-*` directories, preserves non-skill repository metadata such as `README.md`, and validates the resulting root with Skills CLI before publishing. `main` is the unqualified latest-stable install source. Every stable and prerelease tag is an immutable version-selection source using the same tag as Houmao, for example:

```bash
npx skills add https://github.com/igamenovoer/houmao-skills
npx skills add https://github.com/igamenovoer/houmao-skills#v2.0.0
```

Before a release, confirm that the deploy key and secret still exist:

```bash
gh api repos/igamenovoer/houmao-skills/keys --jq '.[] | {title, read_only}'
gh secret list --repo igamenovoer/houmao | rg '^HOUMAO_SKILLS_DEPLOY_KEY'
```

The key listed for release synchronization must report `read_only: false`. To rotate it, create a new Ed25519 key pair in a temporary directory, add its public key as a write-enabled deploy key on `igamenovoer/houmao-skills`, replace the `HOUMAO_SKILLS_DEPLOY_KEY` secret in `igamenovoer/houmao`, and securely remove the temporary private key. Remove the previous deploy key only after a validation run succeeds with the replacement.

Workflow reruns are idempotent when the existing tag already contains the same tree. If a matching tag contains different content, the workflow fails instead of moving it. Treat that failure as a release-integrity incident: inspect the Houmao release tag and mirror tag, and never delete or force-move the published mirror tag as an ordinary retry.

### PyPI Trusted Publisher Setup

In the PyPI project settings for `houmao`, add a trusted publisher with these repository details:

- Owner: `igamenovoer`
- Repository: `houmao`
- Workflow file: `pypi-release.yml`
- Environment: `pypi`

PyPI must trust the workflow file name and the environment name used by the publish job. If either value changes, update the trusted publisher configuration to match before the next release.

## Release Procedure

Recommended release flow:

1. Ensure the release workflow has been merged to `main`.
2. Update any release notes and verify that package metadata still reflects the intended version.
3. Run the pre-publish checks locally:
   - `pixi run lint`
   - `pixi run test`
   - `pixi run typecheck`
   - `pixi run build-dist`
   - `pixi run check-dist`
4. Inspect the built wheel and sdist contents if packaging changes landed since the previous release.
5. Create and push the release tag from `main`:

```bash
git checkout main
git pull --ff-only origin main
git tag v0.4.0
git push origin v0.4.0
```

6. Create and publish the GitHub release for tag `v0.4.0`:

```bash
gh release create v0.4.0 --verify-tag --generate-notes
```

7. Confirm that the `pypi-release` workflow run completes successfully and that PyPI shows the new version.
8. Confirm that the `docs` workflow run triggered by the same release completes successfully and that GitHub Pages reflects the release tag content.
9. Confirm that the `Sync Houmao Skills` workflow publishes the same tag in `igamenovoer/houmao-skills`. For a stable release, confirm that its `main` branch now contains the released root-level skills; for a prerelease, confirm that `main` still points to the latest stable release.

For clarity and conventional GitHub release handling, use `v0.4.0` as the public tag name.

Release candidates should be published as GitHub prereleases, for example `v0.11.0rc1`. A prerelease still publishes the Python package and docs from the release tag. The skills workflow publishes the same prerelease tag in `igamenovoer/houmao-skills` but does not advance the mirror's stable `main` branch. Users can install that prerelease explicitly with a source such as `https://github.com/igamenovoer/houmao-skills#v0.11.0rc1`.

## Release Artifact Scope

Release artifacts are intentionally constrained to the package release surface.

The wheel and sdist are expected to include:

- `src/houmao`
- `README.md`
- `LICENSE`
- `NOTICE`
- `pyproject.toml`

They are expected to exclude repository-only trees and local secret material such as:

- `extern/`
- `openspec/`
- `docs/`
- `tests/`
- `.env`
- `credentials.json`
- `auth.json`

## Current Release-Readiness Baseline

This change implements the release workflow and package publication contract. The release baseline should be refreshed whenever the packaging surface or workflow changes.

Current baseline for this change:

- `pixi run build-dist`: passed
- `pixi run check-dist`: passed
- `pixi run lint`: passed
- source distribution inspection confirmed inclusion of `README.md`, `LICENSE`, `NOTICE`, `pyproject.toml`, and package sources without `extern/`, `openspec/`, `docs/`, `tests/`, `.env`, `credentials.json`, or `auth.json`
- `pixi run docs-build`: fails in pre-existing strict MkDocs validation due broken links and missing anchors outside this release workflow change
- `pixi run typecheck`: fails in pre-existing areas outside this change, with 26 mypy errors across 13 files
- `pixi run test`: fails in pre-existing unit coverage outside this change, with 5 failing tests:
  - `tests/unit/agents/realm_controller/test_cao_client_and_profile.py::test_generate_cao_session_name_adds_conflict_suffix`
  - `tests/unit/agents/realm_controller/test_cli.py::test_mail_command_forwards_cao_parsing_mode_override`
  - `tests/unit/agents/realm_controller/test_runtime_agent_identity.py::test_resolve_agent_identity_name_scans_metadata_for_suffixed_tmux_session`
  - `tests/unit/agents/realm_controller/test_runtime_agent_identity.py::test_resolve_agent_identity_name_fails_when_multiple_suffixed_sessions_match`
  - `tests/unit/agents/realm_controller/test_runtime_registry.py::test_refresh_mailbox_bindings_preserves_success_when_registry_refresh_fails`
- release publication still depends on GitHub environment `pypi` plus matching PyPI trusted publisher configuration

If maintainers choose to release while non-workflow issues remain elsewhere in the repository, record that decision in the release notes or in a follow-up change instead of treating the release workflow as proof that the full repository is green.

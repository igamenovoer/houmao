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
- Authentication: GitHub OIDC trusted publishing, using the GitHub environment `pypi`

Because the workflow is release-driven, the workflow file must already exist on `main` before maintainers publish a release.

## Trusted Publisher Setup

Configure PyPI trusted publishing before creating a release.

### GitHub Repository Setup

Create a GitHub environment named `pypi`.

No repository secret is required for the default publication path. The publish job uses the workflow's OIDC token and `pypa/gh-action-pypi-publish`.

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
git tag v0.3.0
git push origin v0.3.0
```

6. Create and publish the GitHub release for tag `v0.3.0`:

```bash
gh release create v0.3.0 --verify-tag --generate-notes
```

7. Confirm that the `pypi-release` workflow run completes successfully and that PyPI shows the new version.

For clarity and conventional GitHub release handling, use `v0.3.0` as the public tag name.

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

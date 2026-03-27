## Context

Houmao already has package metadata in `pyproject.toml`, local distribution build tasks, and a docs-only GitHub Actions workflow, but it does not have a repository-owned path to publish distributions to PyPI. The repository default branch is `main`, there are no GitHub releases yet, and the first intended public release is `0.1.0`.

The current packaging state also has two release-readiness concerns that should be addressed in the same change:

- the source distribution currently includes unrelated repository content beyond the intended package release surface,
- release metadata is partially duplicated outside package metadata, which increases the chance of version drift during future releases.

This change touches repository automation, packaging configuration, and maintainer release procedure, so a design document is useful before implementation.

## Goals / Non-Goals

**Goals:**
- Add a GitHub Actions workflow that publishes Houmao to PyPI when a GitHub release is published.
- Use current GitHub/PyPI best practices for authentication, preferring trusted publishing over a stored long-lived PyPI token.
- Ensure wheel and sdist artifacts are built once, validated, and published from the same release artifact set.
- Tighten package file selection so public release artifacts include only intended release content.
- Document the maintainer steps required to configure trusted publishing and cut the first `0.1.0` release from the repository.

**Non-Goals:**
- Adding an automatic version bumping system or a full release automation framework beyond GitHub release driven publishing.
- Adding TestPyPI publishing in this change.
- Solving all existing repository test and typecheck failures unless they directly block the release workflow implementation.
- Redesigning unrelated package metadata or documentation outside the release path.

## Decisions

### Trigger publishing from GitHub `release.published`

The repository will publish to PyPI from a workflow triggered by GitHub `release` events with `types: [published]`.

This keeps public publishing tied to an explicit maintainer release action instead of any pushed tag, and it matches GitHub’s release workflow model for stable and prerelease publication. The workflow file should exist on the default branch `main` before maintainers cut the first release.

Alternatives considered:
- Publish on tag push. Rejected because it makes publication easier to trigger accidentally and separates the user-visible GitHub release from the package publication event.
- Publish manually with `workflow_dispatch`. Rejected because it adds an extra release step and weakens the repository-owned release contract.

### Use PyPI trusted publishing through GitHub OIDC

The publish job will authenticate to PyPI through trusted publishing, using GitHub’s OIDC token exchange and a GitHub environment such as `pypi`, rather than storing a long-lived PyPI API token in repository secrets.

This aligns with current PyPI and GitHub guidance, removes the need to keep a permanent credential in the repository, and matches the user’s stated intent to remove the temporary local `.env` token once GitHub-side publishing is configured.

Alternatives considered:
- Store `PYPI_API_TOKEN` as a GitHub Actions secret and upload with username/password. Rejected as the default design because it is weaker operationally than trusted publishing and creates long-lived credential management overhead.
- Continue using the local `.env` token. Rejected because GitHub Actions cannot rely on local uncommitted files and because local tokens are not a repository release workflow.

### Build once, publish from uploaded artifacts

The workflow will use at least two jobs:

- a build job that checks out the repo, sets up Python, builds wheel and sdist, and uploads `dist/` as an artifact,
- a publish job that downloads those exact artifacts and publishes them to PyPI.

This keeps build and publish concerns separate, ensures the published files are exactly the validated files, and allows future extension with additional verification steps without changing the publication contract.

Alternatives considered:
- Build and publish in a single job. Rejected because it is less auditable and makes future validation or approval boundaries harder to enforce.

### Make release artifact scope explicit in Hatch config

The packaging configuration will be tightened so the sdist includes only the intended release surface rather than relying on broad traversal plus exclusions. The preferred direction is to use explicit target-level selection such as `only-include` for the sdist, while keeping the wheel package mapping explicit.

The wheel already looks close to correct, but the current sdist includes unrelated repository trees such as `extern/`, `context/`, and `magic-context/`, which should not ship in a public package release.

Alternatives considered:
- Keep the current include/exclude approach and add more exclusions. Rejected because it is brittle and easy to regress as the repository grows.
- Publish wheel only. Rejected because the project already intends to ship a normal Python source distribution and local build tasks already produce one.

### Treat version consistency as release hygiene, not optional polish

Version-bearing runtime metadata that is intended to describe the package release should be aligned with package metadata before or during this change. The design does not require a full dynamic versioning system, but it does require a single clear source of truth or a simple derived mechanism so future releases do not silently diverge.

Alternatives considered:
- Leave hardcoded runtime version strings in place. Rejected because that makes the first release immediately vulnerable to metadata drift in later patches.

## Risks / Trade-offs

- [Trusted publishing requires GitHub and PyPI configuration outside the repo] → Mitigation: document exact maintainer setup steps and use a dedicated GitHub environment for the publish job.
- [Release automation may publish broken code if maintainers rely only on the trigger] → Mitigation: build and validate artifacts in the workflow and document pre-release checks that maintainers should run before publishing.
- [Tightening sdist scope can accidentally omit files needed for source builds] → Mitigation: keep the release surface explicit, rebuild locally, and verify both `build-dist` and `check-dist` before cutting the release.
- [Version centralization can touch multiple modules] → Mitigation: keep the scope narrow and focus only on user-visible release version surfaces that can drift from package metadata.

## Migration Plan

1. Add the new GitHub Actions publish workflow under `.github/workflows/`.
2. Tighten release artifact selection in `pyproject.toml` and verify the resulting wheel and sdist contents.
3. Align runtime-visible version metadata with package version metadata where needed.
4. Add or update maintainer-facing docs describing PyPI trusted publisher setup, the GitHub `pypi` environment, and the first `v0.1.0` release flow.
5. Configure the trusted publisher on PyPI for this repository and workflow.
6. Create the first GitHub release for version `0.1.0` after the workflow is merged to `main`.

Rollback is simple: disable or revert the workflow and packaging changes, revoke the trusted publisher if needed, and stop cutting GitHub releases until the release path is corrected. No persistent application data migration is involved.

## Open Questions

- Should the repository standardize on tag names `v0.1.0` or bare `0.1.0` for public releases? Current recommendation: use `v0.1.0` for clarity and conventional release handling.
- Should the first release gate on existing `pixi run typecheck` and `pixi run test` failures being resolved, or should this change only establish the publish path and document the current baseline? This affects release readiness policy more than workflow structure.

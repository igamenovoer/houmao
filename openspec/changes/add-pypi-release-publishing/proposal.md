## Why

Houmao has package metadata and local build tasks, but it does not yet have a repository-owned release path that can publish distributions to PyPI from GitHub. Before cutting the first public release, the project needs a repeatable publishing workflow that follows current GitHub and PyPI best practices and avoids relying on a local temporary token in `.env`.

## What Changes

- Add a GitHub Actions workflow that builds release distributions and publishes them to PyPI when a GitHub release is published.
- Use GitHub-to-PyPI trusted publishing as the default authentication model, with repository configuration aligned to current best practices.
- Tighten package release preparation so the published source distribution contains only intended release content.
- Document the operator steps needed to configure PyPI publishing and cut the first public release `0.1.0`.
- Validate the release path against the current package metadata and release workflow expectations before the first public publish.

## Capabilities

### New Capabilities
- `pypi-release-publishing`: Define the repository-owned workflow, packaging constraints, and operator setup required to publish Houmao distributions to PyPI from GitHub releases.

### Modified Capabilities
- None.

## Impact

- Affected code and config: `.github/workflows/`, `pyproject.toml`, release-related documentation, and any version metadata wiring needed for published artifacts.
- External systems: GitHub Actions, GitHub repository environments/settings, and the PyPI project publishing configuration.
- Operator workflow: maintainers will configure trusted publishing in GitHub/PyPI and create the first GitHub release for version `0.1.0`.

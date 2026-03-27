## 1. Release Workflow Automation

- [x] 1.1 Add a GitHub Actions workflow under `.github/workflows/` that triggers on `release.published`, builds wheel and sdist, and uploads the built `dist/` artifacts.
- [x] 1.2 Add a publish job that downloads the built artifacts and publishes them to PyPI through trusted publishing with the intended GitHub environment configuration.
- [x] 1.3 Verify the workflow contract matches the documented repository release path for the first public release from `main`.

## 2. Package Release Hygiene

- [x] 2.1 Tighten Hatch packaging configuration so the source distribution includes only the intended public release files and excludes unrelated repository trees and local secret files.
- [x] 2.2 Align runtime-visible version metadata with package version metadata where release-facing version strings can drift.
- [x] 2.3 Rebuild the release artifacts locally and verify the resulting wheel and sdist contents and metadata are suitable for public publication.

## 3. Maintainer Setup And Release Documentation

- [x] 3.1 Add maintainer-facing documentation for configuring the PyPI trusted publisher and the required GitHub environment/workflow mapping.
- [x] 3.2 Document the release procedure for the first public version `0.1.0`, including the recommended tag/release flow and pre-publish checks.
- [x] 3.3 Record the current release-readiness verification baseline for this change, including any intentionally deferred test or typecheck issues that are outside the workflow implementation itself.

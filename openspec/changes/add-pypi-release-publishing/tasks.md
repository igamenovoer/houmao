## 1. Release Workflow Automation

- [ ] 1.1 Add a GitHub Actions workflow under `.github/workflows/` that triggers on `release.published`, builds wheel and sdist, and uploads the built `dist/` artifacts.
- [ ] 1.2 Add a publish job that downloads the built artifacts and publishes them to PyPI through trusted publishing with the intended GitHub environment configuration.
- [ ] 1.3 Verify the workflow contract matches the documented repository release path for the first public release from `main`.

## 2. Package Release Hygiene

- [ ] 2.1 Tighten Hatch packaging configuration so the source distribution includes only the intended public release files and excludes unrelated repository trees and local secret files.
- [ ] 2.2 Align runtime-visible version metadata with package version metadata where release-facing version strings can drift.
- [ ] 2.3 Rebuild the release artifacts locally and verify the resulting wheel and sdist contents and metadata are suitable for public publication.

## 3. Maintainer Setup And Release Documentation

- [ ] 3.1 Add maintainer-facing documentation for configuring the PyPI trusted publisher and the required GitHub environment/workflow mapping.
- [ ] 3.2 Document the release procedure for the first public version `0.1.0`, including the recommended tag/release flow and pre-publish checks.
- [ ] 3.3 Record the current release-readiness verification baseline for this change, including any intentionally deferred test or typecheck issues that are outside the workflow implementation itself.

## Why

The repository currently exposes tracked credential payloads under `tests/fixtures/agents/tools/*/auth`, including a reachable `auth.json` that fresh clones still receive through normal branch history. This must be fixed now so new clones do not materialize committed secrets and future fixture work cannot accidentally reintroduce credential-bearing files.

## What Changes

- Rewrite reachable repository history so the tracked Codex `auth.json` is no longer present in branch history fetched by new clones.
- Replace tracked credential-bearing fixture files with safe placeholders or structural templates only where fixture shape must remain testable.
- Tighten repository ignore rules so credential env files, token payloads, OAuth state, and similar auth artifacts remain local-only across the repo, including fixture trees.
- Add explicit repo requirements for credential hygiene so tracked agent fixtures may only keep secret-free templates and placeholders.
- **BREAKING** Force-update affected remote refs so branch history no longer contains the leaked credential artifact.

## Capabilities

### New Capabilities
- `repo-credential-hygiene`: Define which auth-related files may be tracked as placeholders or templates, which must remain ignored, and what history rewrite guarantees are required so new clones do not receive leaked credential payloads.

### Modified Capabilities
- `component-agent-construction`: Clarify that tracked auth fixtures used for agent-definition examples and tests must remain secret-free and rely on ignored local-only auth material for real credentials.

## Impact

- Affected systems: git history and remote refs, repository ignore policy, tracked agent fixtures under `tests/fixtures/agents/`, and any documentation or test fixtures that currently rely on tracked auth payloads.
- Affected code and tooling: repo maintenance scripts or operator commands used to rewrite history and force-update refs, plus fixture files that need sanitization.
- Operational impact: leaked credentials must be rotated or revoked outside the repo cleanup, and collaborators with old clones will need to resync after the history rewrite.

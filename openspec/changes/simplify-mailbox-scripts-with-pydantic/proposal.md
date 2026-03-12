## Why

The projected mailbox helper scripts already publish `pydantic` in `rules/scripts/requirements.txt`, but the shared managed mailbox layer still parses request payloads through hand-written dataclasses, `from_payload()` constructors, and many bespoke helper validators. That mismatch makes the mailbox script surface harder to maintain, duplicates validation logic that already exists elsewhere in the repository, and produces less consistent validation errors than the repo's existing pydantic-backed boundaries.

The mailbox registration refactor is still fresh and localized, so this is a good time to simplify the managed mailbox script implementation without changing the mailbox protocol surface. Doing that now keeps future script additions from copying more manual parsing patterns into the shared mailbox rules bundle.

## What Changes

- Make `pydantic` an explicit, required part of the Python managed mailbox helper contract published under `rules/scripts/requirements.txt`, using a minimum-version requirement rather than an exact or upper-bounded pin.
- Replace manual payload parsing in the shared managed mailbox layer with strict pydantic request models for delivery, mailbox-state mutation, repair, registration, and deregistration flows.
- Reuse shared pydantic validation patterns for mailbox addresses, message ids, timestamps, and nested principal or attachment payloads instead of maintaining parallel hand-written validators.
- Standardize managed mailbox script validation failures into one structured JSON error pattern while keeping the existing `--mailbox-root` plus `--payload-file` invocation contract.
- Keep mailbox transport behavior, SQLite mutation semantics, and filesystem layout unchanged while simplifying implementation code and tests.

## Capabilities

### New Capabilities
- `filesystem-mailbox-managed-scripts`: Defines the dependency and strict payload-validation contract for Python managed mailbox helpers projected into `rules/scripts/`.

### Modified Capabilities

## Impact

- Affected code: `src/gig_agents/mailbox/managed.py`, `src/gig_agents/mailbox/protocol.py`, and the projected wrapper scripts under `src/gig_agents/mailbox/assets/rules/scripts/`.
- Affected dependencies: the mailbox-local Python dependency manifest under `rules/scripts/requirements.txt`.
- Affected tests: mailbox unit tests and runtime mailbox contract tests that assert script materialization and validation behavior.
- External contract: no intentional change to managed script filenames, CLI flags, or JSON success shape; the primary externally visible effect is more consistent validation failures for malformed payloads.

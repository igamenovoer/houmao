# docs-managed-launch-prompt-header-reference Specification

## Purpose

Define the reference-page requirements for documenting the Houmao-owned managed launch prompt header — what it contains, when it is prepended, how it interacts with role injection, and how operators opt out through per-launch flags or stored launch-profile policy.

## Requirements

### Requirement: Reference page documents the managed launch prompt header

The docs site SHALL include a reference page at `docs/reference/run-phase/managed-prompt-header.md` describing the Houmao-owned prompt header that is prepended to managed launches by default.

That page SHALL explain:

- what the header is (a Houmao-owned, deterministic block of text prepended to the operator-supplied or role-supplied system prompt before backend role injection runs),
- why it exists (to give every managed agent a small, reliable preamble that identifies the managed lifecycle and points to the packaged system skills),
- the prompt composition order: source role prompt → prompt-overlay resolution (when present) → managed header prepend (when enabled) → backend-specific role injection,
- the default-on policy and the `--managed-header` / `--no-managed-header` opt-out flags on the relevant launch and launch-profile commands,
- where the header policy is persisted in stored launch profiles and how `--clear-managed-header` returns that field to inherit behavior,
- which launch surfaces honor the policy: `houmao-mgr agents launch`, `houmao-mgr project easy instance launch`, and any launch-profile-backed flow built on top of those.

That page SHALL link to:

- `docs/getting-started/launch-profiles.md` for the shared launch-profile conceptual model and persistence rules,
- `docs/reference/run-phase/role-injection.md` for the per-backend role injection mechanism that runs after the header is prepended,
- the `houmao-mgr` CLI reference for the flag-level documentation of `--managed-header` and `--no-managed-header`.

That page SHALL state that the managed header is part of the prompt body delivered to the underlying CLI tool and is not a separate transport channel.

#### Scenario: Reader can find a dedicated reference for the managed prompt header

- **WHEN** a reader navigates the docs site looking for what the managed prompt header contains and when it is added
- **THEN** they find a single reference page under `docs/reference/run-phase/managed-prompt-header.md`
- **AND THEN** the page explains what the header is, why it exists, and when it is prepended

#### Scenario: Reader sees the prompt composition order

- **WHEN** a reader opens the managed prompt header reference page
- **THEN** the page documents the composition order as source role prompt → prompt-overlay resolution → managed header prepend → backend role injection
- **AND THEN** the page explains that the header is prepended before backend role injection rather than appended after it

#### Scenario: Reader sees the opt-out flags and default-on policy

- **WHEN** a reader looks up how to disable the managed header on a launch
- **THEN** the page documents `--no-managed-header` as the per-launch opt-out
- **AND THEN** the page documents `--managed-header` as the explicit opt-in
- **AND THEN** the page states that omitted policy falls back to default-on behavior

#### Scenario: Reader can navigate from header reference to launch-profiles guide and CLI reference

- **WHEN** a reader follows cross-reference links from the managed prompt header reference page
- **THEN** they reach `docs/getting-started/launch-profiles.md` for the shared profile model
- **AND THEN** they reach `docs/reference/cli/houmao-mgr.md` for the flag-level CLI coverage
- **AND THEN** they reach `docs/reference/run-phase/role-injection.md` for the per-backend role injection mechanism

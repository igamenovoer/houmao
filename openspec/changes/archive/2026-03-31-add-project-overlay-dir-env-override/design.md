## Context

Project-aware Houmao behavior currently has two hard assumptions:

1. `houmao-mgr project init` bootstraps the overlay at `<cwd>/.houmao`.
2. Project-aware resolution discovers the active overlay only through nearest-ancestor `.houmao/houmao-config.toml` lookup.

That works for local interactive use, but it is brittle in CI and controlled automation because the active overlay directory cannot be redirected process-locally through the environment. The codebase already uses a consistent precedence pattern for shared roots such as runtime, registry, mailbox, and local jobs: explicit override first, environment override second, built-in default last. This change extends that style to project-overlay selection without introducing a separate "project root" concept.

## Goals / Non-Goals

**Goals:**
- Add a process-local env override that selects the overlay directory for `houmao-mgr project` and project-aware ambient resolution.
- Preserve current defaults when the env var is unset.
- Keep the storage contract rooted directly at the selected overlay directory.
- Make CI and automation able to redirect project-aware lookup without depending on `cwd` and nearest-ancestor discovery.
- Keep overlay selection logic centralized so `project`, `brains build`, `agents launch`, and mailbox wrappers follow the same contract.

**Non-Goals:**
- Introducing a separate project-root abstraction into the project overlay contract.
- Changing the shared Houmao home roots under `~/.houmao/`.
- Adding a new config schema field to recover a logical project root.
- Adding a new explicit `--project-overlay-dir` CLI flag in this first revision.

## Decisions

### Decision 1: `HOUMAO_PROJECT_OVERLAY_DIR` selects the overlay directory directly

`HOUMAO_PROJECT_OVERLAY_DIR` will mean "treat this absolute directory as the active project overlay root".

This makes the contract direct and predictable:

- `houmao-config.toml` lives at `<overlay-root>/houmao-config.toml`
- the catalog lives at `<overlay-root>/catalog.sqlite`
- the compatibility projection lives under `<overlay-root>/agents/`
- the mailbox root lives under `<overlay-root>/mailbox/`

When the env var is unset, the default overlay root remains `<cwd>/.houmao`.

Alternatives considered:
- `HOUMAO_PROJECT_ROOT`: rejected because it implies the repo or workspace root rather than the Houmao overlay directory.
- Keep `.houmao` appended under an env-selected parent directory: rejected because it does not directly override `<cwd>/.houmao`, which is the actual CI pain point.

### Decision 2: Use one shared precedence rule for overlay-aware discovery

The selected overlay root for project-aware discovery will resolve in this order:

1. `HOUMAO_PROJECT_OVERLAY_DIR` when set,
2. nearest-ancestor `.houmao/houmao-config.toml` discovery from the caller's current directory,
3. current default behavior where applicable.

For agent-definition resolution, the existing explicit overrides stay above overlay selection:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. `HOUMAO_PROJECT_OVERLAY_DIR`,
4. nearest-ancestor `.houmao/houmao-config.toml`,
5. default `<cwd>/.houmao/agents`.

When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it is authoritative. If `<overlay-root>/houmao-config.toml` exists, Houmao uses that overlay. If it does not exist, project-aware fallback uses `<overlay-root>/agents` and does not continue to nearest-ancestor discovery from `cwd`.

### Decision 3: Require `HOUMAO_PROJECT_OVERLAY_DIR` to be absolute, but allow init to create it

The env var will be treated like the existing root-relocation env vars in `owned_paths.py`: it must be absolute. Relative values fail early with one operator-facing error.

The selected directory does not need to exist before `project init`; init may create it. For commands that require a discovered overlay, missing `houmao-config.toml` at the env-selected overlay root means "no overlay discovered" rather than "fall back somewhere else".

Alternatives considered:
- Allow relative env values resolved from `cwd`: rejected because it makes CI and nested command behavior harder to reason about.
- Require the overlay directory to already exist: rejected because it adds unnecessary setup friction for `project init`.

### Decision 4: `project status` should be overlay-centric

`project status` is operator-facing inspection, so it should report:

- the resolved `overlay_root`,
- whether that root came from `HOUMAO_PROJECT_OVERLAY_DIR` or ancestor discovery,
- whether a config was discovered under that overlay root,
- the resolved effective agent-definition directory and its source.

This keeps the visible contract aligned with the real anchor of project-aware behavior and avoids reintroducing "project root" terminology.

## Risks / Trade-offs

- [Risk] `HOUMAO_PROJECT_OVERLAY_DIR` may leak into child processes and redirect later Houmao commands unexpectedly. → Mitigation: document it as a process-local override intended for CI and controlled automation.
- [Risk] Operators may expect the env var to point at a repo root instead of the Houmao overlay dir. → Mitigation: use `PROJECT_OVERLAY_DIR` naming consistently in specs, docs, and CLI help.
- [Risk] Commands run with a stale env override may ignore a valid checkout-local overlay. → Mitigation: fail clearly on invalid relative values and document env precedence explicitly.
- [Risk] `project status` output becomes more overlay-specific than earlier wording implied. → Mitigation: report `overlay_root` and its source explicitly so the behavior is inspectable.

## Migration Plan

The change is opt-in.

1. Existing local workflows continue unchanged when `HOUMAO_PROJECT_OVERLAY_DIR` is unset.
2. CI pipelines may export `HOUMAO_PROJECT_OVERLAY_DIR=/abs/path/to/overlay` before running `houmao-mgr project ...`, `houmao-mgr brains build`, or preset-backed launch flows.
3. Documentation updates explain the precedence change and how to unset the env var to return to current behavior.

No stored-data migration or compatibility shim is required.

## Open Questions

- Whether a later follow-up should add an explicit `--project-overlay-dir` flag for parity with the env override.

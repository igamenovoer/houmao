## ADDED Requirements

### Requirement: No `--yolo` references remain in docs as a current option

All files under `docs/` SHALL be swept for stale `--yolo` references. The `--yolo` option was removed in `2026-04-06-remove-launch-yolo-cli-option` and SHALL NOT appear as a supported launch flag anywhere in the docs tree.

Any `--yolo` occurrence SHALL either be removed or rewritten as an explicit "removed in 0.3.x" historical note. The sweep SHALL cover `docs/reference/cli/`, `docs/getting-started/`, and `docs/reference/run-phase/`. Each replacement SHALL be reviewed for surrounding-prose accuracy — not a blind find-and-replace.

#### Scenario: No `--yolo` option references in docs

- **WHEN** searching all `.md` files under `docs/` for `--yolo`
- **THEN** zero matches appear in the context of a current supported flag
- **AND THEN** any remaining mention is in an explicit historical or removal-note context

#### Scenario: Removed-flag rewrites point at the current prompt-mode mechanism

- **WHEN** a `--yolo` reference is rewritten as a historical note
- **THEN** the surrounding prose explains that prompt-mode posture is now controlled through `launch.prompt_mode` in stored profiles or the equivalent launch-profile flags

### Requirement: No stale `specialist` skill identifier references remain

All files under `docs/` SHALL be swept for occurrences of the bare skill identifier `specialist` used as if it were the current packaged Houmao-owned skill name. The current name is `houmao-manage-specialist` (renamed in `2026-04-05-rename-create-specialist-to-manage-specialist`).

The sweep SHALL distinguish:

- legitimate prose use of the noun "specialist" (in phrases like "easy specialist", "specialist creation", "specialist-backed launch") — left unchanged,
- the legacy skill identifier `specialist` or `houmao-create-specialist` used as a current packaged skill — replaced with `houmao-manage-specialist`.

Each replacement SHALL be reviewed in context for accuracy.

#### Scenario: No `houmao-create-specialist` references as current packaged skill

- **WHEN** searching `docs/` for `houmao-create-specialist`
- **THEN** zero matches appear as current packaged skills
- **AND THEN** any remaining mention is in an explicit migration-note context

#### Scenario: Prose use of "specialist" is preserved

- **WHEN** a doc page uses "specialist" as a noun (e.g., "easy specialist", "specialist creation flow")
- **THEN** the sweep does not rewrite that prose use into `houmao-manage-specialist`
- **AND THEN** only the literal skill identifier is rewritten

### Requirement: Verification step covers `agentsys` stragglers introduced after the prior sweep

The earlier `docs-stale-content-removal` requirement to remove `agentsys` references SHALL be reverified during this pass against the current docs tree. Any `agentsys`, `.agentsys`, or `AGENTSYS_` occurrence introduced by content added since the prior sweep SHALL be replaced with the corresponding `houmao` equivalent.

#### Scenario: No `agentsys` references in docs after this pass

- **WHEN** searching all `.md` files under `docs/` for `agentsys`
- **THEN** zero matches are found

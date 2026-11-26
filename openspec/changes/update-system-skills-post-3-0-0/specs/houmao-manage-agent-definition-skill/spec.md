# Spec Delta

## ADDED Requirements

### Requirement: Agent definition skill fixes Qualified Modes table and covers post-3.0.0 launch and DSH flags
`houmao-agent-definition` SHALL fix `references/common/profile-lanes.md` (`Claude: headless|tui`, `Codex: headless|service|tui`, `Kimi: headless|service|tui|web`, `DSH: headless|service|web`) and add `dsh`, `--tool-params`, `--clear-tool-params`, `tool_params.permissions`, `--headless-display-*`, `--reuse-home`, `--relaunch-chat-session-mode`, `--executor`, `--force`, `--agent-id-mode`, `--gateway-admin-seed`, `--system-skill-pack`/`--system-skills-mode`, and `managed_header` v2.

#### Scenario: Authoring and launch pages expose accurate run modes and DSH flags
- **WHEN** an admin creates a specialist, profile, launch dossier, deployment, or easy launch using `dsh`, `service`/`web` modes, or `tool_params`
- **THEN** `references/common/profile-lanes.md` lists exact per-tool qualified modes matching runtime validation
- **AND THEN** `specialists.md`, `profiles.md`, `recipe-profiles.md`, `launch-dossiers.md`, `deployment.md`, and `launch-instance.md` include `dsh` and current post-3.0.0 flags

### Requirement: Agent definition skill reconciles legacy command pages and deduplicates SKILL-MAIN.md
`houmao-agent-definition` SHALL resolve the five unindexed root pages (`create.md`, `get.md`, `list.md`, `remove.md`, `set.md`) and `low-level/raw-profiles.md` against `## Subcommands` and `manifest.toml`, remove inlined launcher and config-draft JSON examples already owned by `references/` and `commands/`, and remove obsolete `houmao-cli` guardrails.

#### Scenario: Entrypoint and command inventory have no duplicate or orphaned pages
- **WHEN** a reviewer inspects `houmao-agent-definition` against `imsight-agent-skill-handling`
- **THEN** `SKILL-MAIN.md` references `references/common/launcher.md` and `commands/` pages instead of inlining duplicate launcher steps and JSON payloads
- **AND THEN** every file under `commands/` maps cleanly to the `## Subcommands` table and `manifest.toml`

### Requirement: Agent definition skill preserves admin gate, alias, minimal drafts, and authoring invariants
`houmao-agent-definition` SHALL preserve admin-only `## Actor Frame Gate`, the `specialist-mgr` compatibility alias, minimal `internals config-drafts generate` payloads, the `definition-authoring` derive/approve/materialize/validate lifecycle, `definition-deployment` and atomic `definition-batch` (`1..32`), saved `--tmux-server`, and no same-root mailbox preregistration.

#### Scenario: Config draft generation and batch deployment preserve strict invariants
- **WHEN** an admin generates a minimal config draft or applies a batch deployment
- **THEN** `config-drafts generate` accepts only minimal `{"fields":{...}}` holes without memo seeds or launch overrides
- **AND THEN** `definition-batch` preserves `--count 1..32`, narrow delegation flags, and no premature per-agent mailbox preregistration

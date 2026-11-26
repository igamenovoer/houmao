# Spec Delta

## ADDED Requirements

### Requirement: Memory manager aligns with Managed Prompt Header v2 memo cues and compact receipts
`houmao-memory-mgr` SHALL align its live-memory guidance with `MANAGED_PROMPT_HEADER_VERSION = 2` `<memo_cue>` semantics (read every turn, apply directly, keep brief, update only when asked or outdated) and compact `memo set|append` write receipts followed by `memo show` inspection.

#### Scenario: Agent updates live memo under prompt header v2
- **WHEN** a managed agent writes or appends to `houmao-memo.md` using `houmao-memory-mgr`
- **THEN** it uses the compact receipt to confirm the write and inspects resulting content via `memory memo show`, honoring `<memo_cue>` discipline

### Requirement: Memory manager decomposes monolithic SKILL-MAIN.md into commands and removes boilerplate
`houmao-memory-mgr` SHALL decompose its 142-line `SKILL-MAIN.md` into a lean ~80-line router plus `commands/{read,write,remove}.md` (each with numbered `## Workflow` and fallback) matching `manifest.toml` `commands`, eliminate duplicated trigger rules, launcher, Missing-Input, and `houmao-cli` boilerplate, and make frontmatter `description` concise.

#### Scenario: Entrypoint and command pages follow progressive disclosure
- **WHEN** a reviewer inspects `houmao-memory-mgr` against `imsight-agent-skill-handling`
- **THEN** `SKILL-MAIN.md` presents a concise `## Workflow`, `## Actor Frame Gate`, `## Subcommands` table (`help`, `read`, `write`, `remove`), and skill-specific `DO NOT ...` guardrails without cross-skill boilerplate

### Requirement: Memory manager preserves trigger discipline, seed-vs-live split, and pages confinement
`houmao-memory-mgr` SHALL preserve its necessary/sufficient trigger rule, strict separation between birth-time profile memo seeds (never passed to `config-drafts`) and live memory (`HOUMAO_AGENT_MEMO_FILE` / `HOUMAO_AGENT_PAGES_DIR` or `agents self|single memory`), smallest meaningful edit, and `pages/` confinement without auto-indexing.

#### Scenario: Profile memo seeds and live memory edits remain strictly separated
- **WHEN** an agent edits a live memo versus a launch-profile memo seed
- **THEN** live edits use `agents self|single memory` or env paths under `pages/` and `houmao-memo.md`, while birth-time seeds use profile/launch-dossier flags and never `config-drafts`

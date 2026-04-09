## ADDED Requirements

### Requirement: houmao-mgr reference dedicates a section to the credentials command group

`docs/reference/cli/houmao-mgr.md` SHALL include a dedicated `credentials` command-group section inside its "Command Groups" heading, parallel to the existing `admin`, `agents`, `brains`, `mailbox`, `project`, `server`, and `system-skills` sections.

That section SHALL:

- present `houmao-mgr credentials` as the first-class top-level credential-management surface,
- document the `claude`, `codex`, and `gemini` tool subcommands and the supported CRUD verbs (`list`, `get`, `add`, `set`, `remove`, `rename`) derived from live Click help output,
- explain how `credentials ...` relates to `project credentials ...` — the top-level family is agent-definition-directory-capable through `--agent-def-dir <path>` and the project-scoped wrapper targets the active project overlay,
- describe when to reach for which surface (plain agent-definition directories vs active project overlays),
- cross-link the packaged `houmao-credential-mgr` system-skill guidance and the existing credential-lane notes in the `project easy` and `project agents tools <tool> auth` sections.

#### Scenario: Reader finds the credentials command group in the reference
- **WHEN** a reader opens `docs/reference/cli/houmao-mgr.md`
- **THEN** the "Command Groups" outline contains an explicit `### credentials — <section title>` heading alongside the other top-level command groups
- **AND THEN** the section is discoverable from the page table of contents without reading unrelated command-group prose first

#### Scenario: Reader understands when to use credentials vs project credentials
- **WHEN** a reader opens the `credentials` section
- **THEN** the page explains that `houmao-mgr credentials <tool> ...` is the dedicated credential-management surface and that `--agent-def-dir <path>` targets plain agent-definition directories outside of any project overlay
- **AND THEN** the page explains that `houmao-mgr project credentials <tool> ...` is the project-scoped wrapper that targets the active Houmao project overlay
- **AND THEN** the page states that the two surfaces share semantics and that the project-scoped wrapper is the preferred entry point when an active overlay is present

#### Scenario: Reader finds supported credentials subcommands per tool
- **WHEN** a reader opens the `credentials` section
- **THEN** the page documents `claude`, `codex`, and `gemini` as the three supported tool subcommands
- **AND THEN** it lists `list`, `get`, `add`, `set`, `remove`, and `rename` as the supported CRUD verbs
- **AND THEN** the supported credential input flags on each tool subcommand (for example `--api-key`, `--auth-token`, `--oauth-token`, `--config-dir`, `--base-url`, `--oauth-creds`) match the current Click decorators at `src/houmao/srv_ctrl/commands/credentials.py`

### Requirement: docs/index.md surfaces the credentials command family

`docs/index.md` SHALL list the `houmao-mgr credentials` command family (or its `houmao-mgr.md` in-page anchor) alongside the other CLI Surfaces entries, so the credentials surface is discoverable from the documentation site landing page.

#### Scenario: Reader finds credentials from the docs landing page
- **WHEN** a reader opens `docs/index.md`
- **THEN** the "CLI Surfaces" section either links directly to the `credentials` heading inside `docs/reference/cli/houmao-mgr.md` or lists the `credentials` command family as a top-level entry point
- **AND THEN** a reader arriving via `docs/index.md` never has to guess that `houmao-mgr credentials` exists

### Requirement: CLI reference documents headless execution overrides on all supported prompt surfaces

`docs/reference/cli/houmao-mgr.md` (and its child reference pages for `agents turn` and `agents gateway`) SHALL document the request-scoped headless execution overrides on every supported prompt submission CLI surface.

At minimum the coverage SHALL include:

- `houmao-mgr agents prompt`
- `houmao-mgr agents turn submit`
- `houmao-mgr agents gateway prompt`

For each of those three surfaces the reference SHALL document:

- `--model TEXT` as a request-scoped headless execution model override,
- `--reasoning-level INTEGER` as a normalized `1..10` reasoning override that does not use any vendor-native knob,
- that the overrides apply to exactly the submitted prompt, turn, or gateway request and do not mutate launch profiles, recipes, specialists, manifests, stored easy profiles, or any other live session defaults,
- that the overrides are rejected clearly when the resolved target is a TUI-backed prompt route rather than silently dropped,
- that partial overrides (for example supplying `--reasoning-level` without `--model`) merge with launch-resolved model defaults through the shared headless resolution helper rather than resetting fields that were not explicitly overridden.

#### Scenario: Reader finds headless overrides on agents prompt
- **WHEN** a reader opens the `agents prompt` coverage inside `docs/reference/cli/houmao-mgr.md`
- **THEN** the page documents `--model` and `--reasoning-level` as supported options
- **AND THEN** the page states that those overrides apply to exactly the submitted prompt and never rewrite persistent launch-resolved state

#### Scenario: Reader finds headless overrides on agents turn submit
- **WHEN** a reader opens the `agents turn submit` coverage
- **THEN** the page documents `--model` and `--reasoning-level` as request-scoped overrides
- **AND THEN** the page explains that those overrides apply only to the submitted turn

#### Scenario: Reader finds headless overrides on agents gateway prompt
- **WHEN** a reader opens the `agents gateway prompt` coverage
- **THEN** the page documents `--model` and `--reasoning-level` as request-scoped overrides
- **AND THEN** the page explains that the overrides apply to exactly the addressed gateway prompt submission, including when that submission is queued through `submit_prompt`

#### Scenario: Reader understands TUI-target rejection
- **WHEN** a reader looks up any of the three supported prompt surfaces
- **THEN** the reference states that supplying `--model` or `--reasoning-level` for a TUI-backed target results in a clear failure rather than a silent drop
- **AND THEN** the reference does not suggest that TUI-backed sessions can be retargeted to a different model through these flags

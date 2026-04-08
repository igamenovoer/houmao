# houmao-mailbox-mgr-skill Specification

## Purpose
Define the packaged Houmao-owned mailbox-administration skill for filesystem mailbox roots, project mailbox roots, and late local managed-agent mailbox binding.

## Requirements

### Requirement: Houmao provides a packaged `houmao-mailbox-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-mailbox-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents and operators to handle mailbox-administration work through these maintained command surfaces:

- `houmao-mgr mailbox init|status|register|unregister|repair|cleanup`
- `houmao-mgr mailbox accounts list|get`
- `houmao-mgr mailbox messages list|get`
- `houmao-mgr project mailbox init|status|register|unregister|repair|cleanup`
- `houmao-mgr project mailbox accounts list|get`
- `houmao-mgr project mailbox messages list|get`
- `houmao-mgr agents mailbox status|register|unregister`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects local action-specific documents rather than flattening the entire workflow into one page.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `houmao-mgr agents mail ...`
- shared gateway `/v1/mail/*` operations
- `houmao-mgr agents gateway mail-notifier ...`
- direct gateway `/v1/mail-notifier` or `/v1/wakeups`
- ad hoc filesystem editing inside mailbox roots

#### Scenario: Installed skill points the caller at maintained mailbox-admin surfaces
- **WHEN** an agent or operator opens the installed `houmao-mailbox-mgr` skill
- **THEN** the skill directs the caller to the maintained mailbox-root, project-mailbox, and late agent-binding command surfaces
- **AND THEN** it does not redirect the caller to unrelated actor-scoped mail, gateway reminder, or direct filesystem mutation paths

#### Scenario: Installed skill routes through action-specific local guidance
- **WHEN** an agent reads the installed `houmao-mailbox-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for mailbox-admin actions
- **AND THEN** the detailed workflow lives in local action-specific documents rather than one flattened entry page

### Requirement: `houmao-mailbox-mgr` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-mailbox-mgr` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed mailbox-admin action selected through the packaged skill.

#### Scenario: PATH launcher is preferred before development probing
- **WHEN** `command -v houmao-mgr` succeeds in the current workspace
- **THEN** the skill tells the agent to use that PATH-resolved `houmao-mgr` command for the turn
- **AND THEN** it does not probe `.venv`, Pixi, or project-local uv launchers first

#### Scenario: uv fallback is used when PATH lookup fails
- **WHEN** `command -v houmao-mgr` fails in the current workspace
- **THEN** the skill tells the agent to try `uv tool run --from houmao houmao-mgr`
- **AND THEN** it treats that uv-managed launcher as the ordinary next fallback because Houmao is officially installed through uv tools

#### Scenario: Development launchers are later defaults, not first probes
- **WHEN** `command -v houmao-mgr` fails
- **AND WHEN** the uv-managed fallback does not satisfy the turn
- **AND WHEN** the current workspace provides development launchers such as Pixi, repo-local `.venv`, or project-local uv
- **THEN** the skill tells the agent to choose an appropriate development launcher for that workspace
- **AND THEN** it does not treat those development launchers as the default first search path

#### Scenario: Explicit user launcher choice overrides the default order
- **WHEN** the user explicitly asks to use `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, project-local `uv run houmao-mgr`, or another specific launcher
- **THEN** the skill tells the agent to honor that requested launcher
- **AND THEN** it does not replace the user-requested launcher with the default PATH-first or uv-fallback choice

### Requirement: `houmao-mailbox-mgr` routes mailbox-admin work by mailbox scope and keeps transport boundaries honest
The packaged `houmao-mailbox-mgr` skill SHALL tell the agent to recover omitted mailbox-admin inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL select mailbox-admin commands by mailbox scope:

- use `houmao-mgr mailbox ...` for arbitrary filesystem mailbox roots,
- use `houmao-mgr project mailbox ...` for overlay-local mailbox roots,
- use `houmao-mgr agents mailbox ...` for late filesystem mailbox binding on an existing local managed agent.

The skill SHALL describe the maintained mailbox-admin CLI in v1 as filesystem-oriented for mailbox root and registration lifecycle.

When transport-specific Stalwart context matters, the skill SHALL describe Stalwart as a mailbox transport/bootstrap boundary and SHALL NOT invent a peer `houmao-mgr mailbox ...` administration lane for Stalwart roots or accounts that does not exist.

The skill SHALL direct ordinary mailbox participation work to `houmao-agent-email-comms` and notifier-round mailbox work to `houmao-process-emails-via-gateway`.

#### Scenario: Arbitrary mailbox-root work uses the generic mailbox family
- **WHEN** the user asks to bootstrap, inspect, repair, clean, or inspect registrations under one non-project filesystem mailbox root
- **THEN** the skill directs the caller to `houmao-mgr mailbox ...`
- **AND THEN** it does not force the project overlay mailbox lane

#### Scenario: Project-local mailbox work uses the project mailbox family
- **WHEN** the user asks to manage mailbox state under the active project overlay
- **THEN** the skill directs the caller to `houmao-mgr project mailbox ...`
- **AND THEN** it does not require an explicit mailbox-root override when the project-scoped lane is the intended maintained surface

#### Scenario: Existing local managed agent mailbox attachment uses the late binding family
- **WHEN** the user asks to inspect, add, or remove filesystem mailbox support for one existing local managed agent
- **THEN** the skill directs the caller to `houmao-mgr agents mailbox ...`
- **AND THEN** it does not reinterpret that request as generic instance lifecycle or actor-scoped mailbox work

#### Scenario: Stalwart remains a documented boundary rather than a fake admin lane
- **WHEN** the current task asks about Stalwart mailbox setup or lifecycle in the context of mailbox administration
- **THEN** the skill describes Stalwart using transport/bootstrap references and current maintained runtime boundaries
- **AND THEN** it does not invent unsupported `houmao-mgr mailbox ...` root or account administration commands for the Stalwart transport

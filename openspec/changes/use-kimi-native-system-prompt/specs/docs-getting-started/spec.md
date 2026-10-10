## MODIFIED Requirements

### Requirement: Quickstart guide covers build and launch
The getting-started section SHALL include a quickstart page that teaches the current recommended first-run Houmao workflow as agent-driven use through installed Houmao system skills. The page SHALL help a reader start from their existing CLI-agent surface, install or project Houmao system skills, invoke `houmao-touring`, and ask that agent for a useful managed-agent outcome.

The quickstart SHALL:

- present the user's current CLI agent as the primary operator of Houmao workflows,
- explain that Houmao system skills guide that CLI agent toward maintained `houmao-mgr` command surfaces,
- show the preferred installed-user setup path with `uv tool install houmao`, `tmux` verification, and `npx skills add https://github.com/igamenovoer/houmao-skills` when `npx` and internet access are available,
- show the Houmao-owned `houmao-mgr system-skills install --tool <tool>[,<tool>...]` path for offline, installed-package-local, explicit-home, pack, symlink/copy, or cleanup needs,
- include a from-source note that source checkout commands use `pixi run houmao-mgr ...` while installed users use `houmao-mgr ...`,
- instruct the reader to start Claude Code, Codex, Kimi 0.34.0 or later, or another maintained CLI-agent surface from the target project directory and ask for `$houmao-touring start a guided tour`,
- include a first useful agent-mediated prompt that asks the user's CLI agent to create or select a specialist, prepare a reusable project profile when useful, launch a managed agent, send an initial prompt, inspect the result, and stop or leave the agent running according to the user's instruction,
- explain the resulting concepts in user-facing terms: project overlay, specialist, project profile, managed agent, gateway, messaging, inspection, memory, mailbox, and loop follow-up,
- state that manual command examples are the underlying machinery the agent may run, manual fallback for debugging, or source-developer reference rather than the primary first-run path,
- preserve direct command examples for project initialization, specialist/profile authoring, launch, prompt or gateway-backed communication, inspection, and stop in a compact fallback or reference section,
- preserve `agents self join` as the supported adoption workflow for an already-running provider TUI and position it after the primary agent-driven path,
- keep the `agents self join` Mermaid sequence diagram or an equivalent diagram illustrating adoption from provider TUI to managed-agent registry/gateway artifacts,
- use current supported command surfaces such as `houmao-mgr project init`, `houmao-mgr project specialist ...`, `houmao-mgr project profile ...`, `houmao-mgr project agents launch|stop`, `houmao-mgr agents single ...`, `houmao-mgr agents self ...`, and `houmao-mgr system-skills ...`,
- avoid presenting retired or removed surfaces such as `houmao-cli`, standalone `houmao-server`, standalone CAO launcher workflows, `agents terminate`, `agents self system-prompt show`, or manual `.agentsys` setup as current first-run guidance,
- link to the maintained getting-started, gateway, mailbox, and CLI references when those concepts appear.

The overview and quickstart SHALL present Kimi Code 0.34.0 or later as a primary supported provider alongside Claude and Codex. They SHALL state that Kimi releases before 0.34.0 are unsupported, support has no upper version limit, and managed role prompts are applied natively before startup. They SHALL not instruct readers to invoke a role-delivery skill or send a role bootstrap turn.

#### Scenario: Quickstart starts with the agent-driven path
- **WHEN** a new reader opens `docs/getting-started/quickstart.md`
- **THEN** the first workflow teaches them to install Houmao and Houmao system skills, start their CLI agent in the target project, and invoke `houmao-touring`
- **AND THEN** the page presents manual `houmao-mgr` command sequences only after the agent-driven entrypoint is established

#### Scenario: Reader sees a first useful managed-agent outcome
- **WHEN** a reader follows the primary quickstart workflow
- **THEN** they see an outcome-oriented prompt covering specialist selection, profile preparation, launch, prompting, inspection, and follow-up or stop
- **AND THEN** the page explains those steps as Houmao outcomes rather than requiring every command manually

#### Scenario: Source checkout readers understand launcher translation
- **WHEN** a source checkout reader follows the quickstart
- **THEN** the page explains that installed-user examples using `houmao-mgr ...` translate to `pixi run houmao-mgr ...` in the source checkout
- **AND THEN** the page does not require installed users to run `pixi install && pixi shell`

#### Scenario: Manual fallback uses maintained command surfaces
- **WHEN** a reader reaches the manual fallback or underlying-machinery section
- **THEN** the examples use maintained `houmao-mgr` command families for project setup, specialist and profile authoring, launch, communication, inspection, stop, system-skill installation, and join
- **AND THEN** the examples do not use removed command or auto-skill surfaces

#### Scenario: Join is documented as adoption
- **WHEN** a reader already has a provider TUI running in tmux
- **THEN** the quickstart provides an `agents self join` adoption workflow after the primary first-run path
- **AND THEN** it illustrates Houmao wrapping the existing provider session with managed-agent artifacts

#### Scenario: Kimi reader sees native role delivery and version floor
- **WHEN** a reader follows the Kimi quickstart path
- **THEN** the page requires Kimi 0.34.0 or later with no upper limit and describes native pre-start role-prompt application
- **AND THEN** it contains no auto-skill or bootstrap-role workaround

### Requirement: Getting-started guidance describes maintained current Kimi behavior
Getting-started pages SHALL describe Kimi 0.34.0 as the minimum supported version and SHALL state that later Kimi versions remain supported without an upper limit. They SHALL explain that Houmao projects the complete effective role prompt through the managed Kimi home's native `SYSTEM.md` before startup and SHALL not document pre-0.34 behavior, managed auto-skill role delivery, manual role bootstrap, or policy-changing chat commands.

#### Scenario: New reader sees current Kimi baseline
- **WHEN** a reader opens the overview, quickstart, or system-skills overview
- **THEN** the guidance describes the maintained Kimi `>=0.34.0` native prompt contract with no upper limit
- **AND THEN** it contains no pre-0.34 compatibility claim or workaround

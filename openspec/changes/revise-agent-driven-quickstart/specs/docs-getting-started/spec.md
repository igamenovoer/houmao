## MODIFIED Requirements

### Requirement: Quickstart guide covers build and launch

The getting-started section SHALL include a quickstart page that teaches the current recommended first-run Houmao workflow as agent-driven use through installed Houmao system skills. The page SHALL help a reader start from their existing CLI-agent surface, install or project Houmao system skills, invoke `houmao-touring`, and ask that agent for a useful managed-agent outcome.

The quickstart SHALL:

- present the user's current CLI agent as the primary operator of Houmao workflows,
- explain that Houmao system skills guide that CLI agent toward maintained `houmao-mgr` command surfaces,
- show the preferred installed-user setup path with `uv tool install houmao`, `tmux` verification, and `npx skills add igamenovoer/tool-skills/houmao` when `npx` and internet access are available,
- show the Houmao-owned `houmao-mgr system-skills install --tool <tool>[,<tool>...]` path for offline, installed-package-local, explicit-home, named-set, subset-skill, symlink/copy, or cleanup needs,
- include a from-source note that source checkout commands use `pixi run houmao-mgr ...` while installed users use `houmao-mgr ...`,
- instruct the reader to start Claude Code, Codex, Gemini, or another supported CLI-agent surface from the target project directory and ask for `$houmao-touring start a guided tour`,
- include a first useful agent-mediated prompt that asks the user's CLI agent to create or select a specialist, prepare a reusable project profile when useful, launch a managed agent, send an initial prompt, inspect the result, and stop or leave the agent running according to the user's instruction,
- explain the resulting concepts in user-facing terms: project overlay, specialist, project profile, managed agent, gateway, messaging, inspection, memory, mailbox, and loop follow-up,
- state that manual command examples are the underlying machinery the agent may run, manual fallback for debugging, or source-developer reference rather than the primary first-run path,
- preserve direct command examples for project initialization, specialist/profile authoring, launch, prompt or gateway-backed communication, inspection, and stop in a compact fallback or reference section,
- preserve `agents self join` as the supported adoption workflow for an already-running provider TUI and position it after the primary agent-driven path,
- keep the `agents self join` Mermaid sequence diagram or an equivalent diagram illustrating adoption from provider TUI to managed-agent registry/gateway artifacts,
- use current supported command surfaces such as `houmao-mgr project init`, `houmao-mgr project specialist ...`, `houmao-mgr project profile ...`, `houmao-mgr project agents launch|stop`, `houmao-mgr agents single ...`, `houmao-mgr agents self ...`, and `houmao-mgr system-skills ...`,
- avoid presenting retired or removed surfaces such as `houmao-cli`, standalone `houmao-server`, standalone CAO launcher workflows, `agents terminate`, or manual `.agentsys` setup as current first-run guidance,
- link to `docs/getting-started/system-skills-overview.md`, `docs/getting-started/easy-specialists.md`, `docs/getting-started/launch-profiles.md`, `docs/getting-started/managed-memory-dirs.md`, gateway and mailbox references when those concepts appear, and `docs/reference/cli/houmao-mgr.md` or dedicated CLI reference pages for flag-level details.

#### Scenario: Quickstart starts with the agent-driven path

- **WHEN** a new reader opens `docs/getting-started/quickstart.md`
- **THEN** the first workflow teaches them to install Houmao and Houmao system skills, start their CLI agent in the target project, and invoke `houmao-touring`
- **AND THEN** the page presents manual `houmao-mgr` command sequences only after the agent-driven entrypoint is established

#### Scenario: Reader sees a first useful managed-agent outcome

- **WHEN** a reader follows the primary quickstart workflow
- **THEN** they see an outcome-oriented prompt they can give to their CLI agent
- **AND THEN** the prompt covers creating or selecting a specialist, preparing a project profile when useful, launching a managed agent, prompting it, inspecting the result, and handling stop or follow-up
- **AND THEN** the page explains those steps as Houmao outcomes rather than requiring the reader to type every command manually

#### Scenario: Source checkout readers understand launcher translation

- **WHEN** a source checkout reader follows the quickstart
- **THEN** the page explains that installed-user examples using `houmao-mgr ...` translate to `pixi run houmao-mgr ...` in the source checkout
- **AND THEN** the page does not require installed users to run `pixi install && pixi shell`

#### Scenario: Manual fallback uses maintained command surfaces

- **WHEN** a reader reaches the manual fallback or underlying-machinery section
- **THEN** the examples use maintained `houmao-mgr` command families for project setup, specialist/profile authoring, launch, prompt or gateway communication, inspection, stop, system-skill installation, and join
- **AND THEN** the examples do not use removed or retired command surfaces as recommended current guidance

#### Scenario: Join is documented as adoption

- **WHEN** a reader already has a provider TUI running in tmux
- **THEN** the quickstart provides an `agents self join` adoption workflow
- **AND THEN** that workflow appears after the primary agent-driven first-run path
- **AND THEN** it includes a Mermaid sequence diagram or equivalent visual showing Houmao wrapping the existing provider session with managed-agent artifacts

### Requirement: Quickstart covers both workflows end-to-end without truncation

The quickstart page at `docs/getting-started/quickstart.md` SHALL present the primary agent-driven workflow and the secondary provider-session adoption workflow completely:

- **Primary workflow (Agent-driven first run)**: from installing Houmao and system skills through invoking `houmao-touring`, requesting a first managed-agent outcome, understanding created project/runtime concepts, and choosing stop or follow-up.
- **Secondary workflow (Join)**: from an already-running provider TUI in tmux through `agents self join`, managed-agent control, inspection, and stop or cleanup.

Manual fallback command sections SHALL be complete enough for a reader to understand the underlying maintained commands without being cut off mid-flow.

#### Scenario: Primary workflow is complete

- **WHEN** a reader follows the primary agent-driven workflow in the quickstart
- **THEN** they can reach a first managed-agent outcome without encountering a truncated section
- **AND THEN** they can find next links for deeper specialist, profile, system-skill, gateway, mailbox, memory, and CLI reference material

#### Scenario: Join workflow is complete

- **WHEN** a reader follows the secondary join workflow in the quickstart
- **THEN** they can complete the provider TUI adoption, inspect or prompt the managed agent, and stop or clean up the managed agent without encountering a truncated section

#### Scenario: Manual fallback is complete enough for debugging

- **WHEN** a reader needs to debug or manually reproduce what the agent-driven path does
- **THEN** the quickstart includes compact maintained command examples or links for each major stage rather than ending mid-command sequence

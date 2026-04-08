## ADDED Requirements

### Requirement: System-skills reference documents the packaged `houmao-project-mgr` skill and its project-management boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-project-mgr` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned project-management entry point across:

- `houmao-mgr project init`
- `houmao-mgr project status`
- `houmao-mgr project agents launch-profiles ...`
- `houmao-mgr project easy instance list|get|stop`

That page SHALL explain that `houmao-project-mgr` covers project overlay discovery and bootstrap guidance, `.houmao/` layout and compatibility-projection explanations, and the project-aware side effects that appear on other command families when a project overlay exists.

That page SHALL explain that neighboring renamed packaged skills keep their current ownership boundaries:

- `houmao-specialist-mgr` owns easy specialist and easy profile authoring plus easy `launch|stop`
- `houmao-credential-mgr` owns project-local auth bundle CRUD
- `houmao-agent-definition` owns low-level roles and recipes
- `houmao-agent-instance` owns generic managed-agent lifecycle after project-scoped routing
- `houmao-mailbox-mgr` owns mailbox-administration guidance

#### Scenario: Reader sees the packaged project-management skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-project-mgr` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering project overlay lifecycle, launch-profile management, and project-scoped easy-instance inspection or stop routing

#### Scenario: Reader sees the boundary between project-management and neighboring renamed skills
- **WHEN** a reader opens the packaged project-management skill section of `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-project-mgr` from `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-instance`, and `houmao-mailbox-mgr`
- **AND THEN** it does not use obsolete `houmao-manage-*` identifiers as the current routing targets

## MODIFIED Requirements

### Requirement: System-skills reference documents the packaged agent-instance lifecycle skill and its boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-instance` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for managed-agent instance lifecycle guidance across:

- `agents launch`
- `project easy instance launch`
- `agents join`
- `agents list`
- `agents stop`
- `agents cleanup session|logs`

That page SHALL explain that `houmao-agent-instance` remains the canonical lifecycle skill while `houmao-agent-messaging` becomes the canonical ordinary communication/control and mailbox-routing skill for already-running managed agents, `houmao-agent-email-comms` remains the ordinary mailbox operations skill, `houmao-agent-gateway` becomes the canonical gateway-specific skill, and `houmao-project-mgr` owns project-scoped `project easy instance list|get|stop` plus project launch-profile authoring guidance.

That page SHALL explain that mailbox surfaces, prompting, mailbox routing, ordinary mailbox operations, gateway-only services, reset-context guidance, specialist CRUD, and project-aware `project easy instance list|get|stop` remain outside the packaged `houmao-agent-instance` skill scope.

That page SHALL describe the CLI-default system-skill install selection as including the packaged project-management, specialist-management, credential-management, agent-definition, agent-instance, agent-messaging, and agent-gateway skills.

That page SHALL explain that managed launch and managed join auto-install the project-management, messaging, and gateway skills through the packaged `user-control`, `agent-messaging`, and `agent-gateway` sets but do not auto-install the separate lifecycle-only `houmao-agent-instance` skill.

#### Scenario: Reader sees the packaged lifecycle skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-instance` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent instance lifecycle rather than gateway or messaging guidance

#### Scenario: Reader sees the boundary between project, lifecycle, messaging, and gateway skills
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-agent-instance` from `houmao-project-mgr`, `houmao-agent-messaging`, and `houmao-agent-gateway`
- **AND THEN** it explains that prompting and mailbox routing belong to messaging, ordinary mailbox operations belong to the mailbox skill family, project-aware `project easy instance list|get|stop` belongs to `houmao-project-mgr`, and gateway lifecycle, discovery, and gateway-only services belong to the gateway skill

#### Scenario: Reader sees the updated default install behavior
- **WHEN** a reader checks the install-selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page explains that CLI-default installation includes project-management, lifecycle, messaging, and gateway skills
- **AND THEN** it explains that managed launch and managed join auto-install the project-management, messaging, and gateway skills without auto-installing the lifecycle-only skill

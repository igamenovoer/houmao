# Spec Delta

## ADDED Requirements

### Requirement: Gateway notifier prompts use public native mailbox entrypoints

With both managed-agent routing siblings installed, a notifier prompt SHALL direct the agent to `houmao-agent-entrypoint` using the tool's native skill interface. It SHALL supply the processing route, current gateway base URL, selected `offline` or `online` channel, and current expected binding ID. It SHALL keep private skill files and protected child lookups out of the prompt.

#### Scenario: Codex notifier prompt uses a native installed-skill trigger

- **WHEN** the gateway renders a wake-up prompt for a mailbox-enabled Codex session with installed Houmao mailbox skills
- **THEN** the prompt uses Codex-native installed-skill invocation for `houmao-agent-entrypoint process-emails-via-gateway`
- **AND THEN** it does not mention `skills/mailbox/.../SKILL.md` or copied project-local skill paths

#### Scenario: Claude notifier prompt avoids project-local skill-document paths

- **WHEN** the gateway renders a wake-up prompt for a mailbox-enabled Claude session with installed Houmao mailbox skills
- **THEN** the prompt directs Claude to use the installed public `houmao-agent-entrypoint` through the native Claude skill surface
- **AND THEN** it does not mention `skills/.../SKILL.md` as the operational contract for that round

#### Scenario: Hermes opens the public mailbox entrypoint

- **WHEN** a managed Hermes session has both public skill siblings and receives a notifier prompt
- **THEN** the prompt instructs Hermes to load `houmao-agent-entrypoint` with `skill_view` and select `process-emails-via-gateway` with the current gateway URL, channel, and expected binding ID
- **AND THEN** it leaves the protected child to delegation through `houmao-shared-routines` after verified self
- **AND THEN** it identifies `agent-email-comms` as the public entrypoint route for ordinary mail outside the notified round

#### Scenario: An incomplete skill installation uses the selected mailbox API

- **WHEN** either required public skill sibling is missing from the target session
- **THEN** the prompt uses the supported mailbox API fallback for the supplied gateway URL, channel, and expected binding ID
- **AND THEN** it omits native skill lookup and makes no claim that the protected routine is available

## MODIFIED Requirements

### Requirement: Gateway notifier wake-up prompts instruct archive-after-processing workflow

When the gateway mail notifier enqueues a reminder for open Inbox work, the prompt SHALL announce Inbox mail and select the public processing route when both required public skills are installed. It SHALL direct the agent to list Inbox work through the gateway mailbox API, process relevant mail, follow the binding's authorized completion path for successfully processed messages, and stop after the round.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The prompt SHALL distinguish safe triage from mutating reads. It SHALL summarize the applicable gateway routes for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive` according to the selected binding's capabilities and the session's authority.

The prompt SHALL reserve runtime archive for bindings that authorize it. On a protected binding, it SHALL direct the agent to report successfully processed mail for independently authorized owner archive through the backend. It SHALL omit runtime placement operations from the available routes and keep reading and marking read separate from completion.

#### Scenario: Prompt names archive as completion

- **WHEN** the notifier enqueues a wake-up prompt for open Inbox work
- **THEN** the prompt identifies archive of successfully processed mail as completion through the binding's authorized path
- **AND THEN** it keeps mark-read as a read-state change

#### Scenario: Prompt advertises peek and read separately

- **WHEN** the notifier prompt provides the current mailbox gateway operation contract and the binding supports both peek and read
- **THEN** it lists separate routes or action names for peeking and reading mail
- **AND THEN** it communicates that peeking leaves read state unchanged

#### Scenario: Protected Binding Directs Processed Mail to Owner Archive

- **WHEN** the notifier renders a prompt for a protected mailbox binding
- **THEN** it directs the agent to report successfully processed mail for independently authorized owner archive
- **AND THEN** the advertised runtime routes exclude ordinary archive, move, and archived-state updates

### Requirement: Gateway notifier has no Gemini prompt specialization
Gateway mail-notifier prompt rendering SHALL NOT contain Gemini-specific skill invocation, destination paths, or provider branches.

#### Scenario: Maintained notifier providers exclude Gemini
- **WHEN** notifier guidance is rendered for a maintained provider
- **THEN** it uses the applicable native skill guidance for that provider
- **AND THEN** no Gemini prompt branch is selectable

## REMOVED Requirements

### Requirement: Gateway notifier prompts use native mailbox-skill invocation and never surface skill-document paths

**Reason**: The prior requirement included an unsupported Gemini prompt and predated the parent-scoped mailbox layout.

**Migration**: Use the public native notifier entrypoint. Load only the selected protected routine through the shared sibling.

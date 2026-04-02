## ADDED Requirements

### Requirement: Gemini demo lane uses native installed Houmao mailbox skills
For the maintained Gemini lane, the supported `single-agent-gateway-wakeup-headless` demo SHALL exercise the Gemini mailbox-system-skill contract through installed Houmao-owned Gemini skills under `.agents/skills/` and SHALL NOT depend on a project-local `skills/mailbox/...` mirror for ordinary runtime prompting.

#### Scenario: Gemini demo prompt uses installed Houmao skill by name
- **WHEN** the demo automatic or stepwise wake-up flow targets tool `gemini`
- **THEN** the maintained Gemini prompt tells the agent to use the installed `houmao-process-emails-via-gateway` skill by name for the current wake-up round
- **AND THEN** the demo does not require a project-local `skills/mailbox/.../SKILL.md` path to make the Gemini lane succeed

## MODIFIED Requirements

### Requirement: The demo SHALL verify completion through gateway evidence, headless managed-agent evidence, output creation, and actor-scoped unread completion
The supported demo SHALL treat success as all of the following:

- gateway notifier evidence shows unread work was detected and processed,
- the headless managed-agent inspection surface records execution evidence for the delivered work,
- the agent creates the requested artifact under the copied project's `tmp/` directory,
- `houmao-mgr agents mail check --unread-only` reaches zero actionable unread messages for the selected agent.

`houmao-mgr project mailbox messages list|get` SHALL remain structural inspection only within this demo and SHALL be used to corroborate message identity, folder, projection path, canonical path, sender, recipients, subject, body, and attachments rather than authoritative read-state.

The maintained demo SHALL wait for gateway and headless terminal evidence to settle before declaring verification failure when the requested project artifact and mailbox side effects have already occurred.

For headless verification, the demo SHALL accept durable terminal turn artifacts as canonical headless completion evidence even when optional headless detail metadata such as `completion_source` is absent.

#### Scenario: Demo verifies actor-scoped unread completion
- **WHEN** the demo verifies one completed run after the delivered message is processed
- **THEN** it checks `houmao-mgr agents mail check --unread-only` for zero actionable unread messages
- **AND THEN** it does not require project-mailbox inspection to report a global `read: true` state

#### Scenario: Demo verifies headless managed-agent evidence without relying on TUI posture
- **WHEN** the demo verifies one completed headless run after the delivered message is processed
- **THEN** it collects managed-agent headless evidence from existing managed-agent inspection surfaces or durable turn artifacts
- **AND THEN** it uses that evidence as the canonical runtime-observation complement to gateway notifier evidence
- **AND THEN** it does not require parser-owned TUI ready-posture evidence in order to declare the headless run complete

#### Scenario: Demo waits for settled gateway and headless completion evidence
- **WHEN** the delivered message has already been processed and the expected project artifact already exists
- **AND WHEN** gateway queue state or managed-agent headless detail has not yet reconciled to terminal evidence
- **THEN** the demo verification flow waits for those terminal gateway and headless signals to settle before failing the run
- **AND THEN** it does not snapshot a transient in-between state as the final maintained verification result

#### Scenario: Demo verifies the requested project artifact
- **WHEN** the delivered message asks the agent to write one deterministic file
- **THEN** the demo verifies that file under `<output-root>/project/tmp/`
- **AND THEN** it verifies that the created artifact matches the expected deterministic content for that run

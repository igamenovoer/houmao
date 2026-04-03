## RENAMED Requirements

- FROM: `Gemini demo lane uses native installed Houmao mailbox skills`
- TO: `Maintained demo lanes use native installed Houmao mailbox skills`

## MODIFIED Requirements

### Requirement: Maintained demo lanes use native installed Houmao mailbox skills
For the maintained Claude, Codex, and Gemini lanes, the supported `single-agent-gateway-wakeup-headless` demo SHALL exercise the mailbox-system-skill contract through installed Houmao-owned mailbox skills in the selected runtime home and SHALL NOT depend on a project-local `skills/mailbox/...` mirror or copied `SKILL.md` path for ordinary runtime prompting.

For maintained wake-up rounds:
- Claude guidance SHALL use the installed Houmao mailbox skill through Claude's native skill surface.
- Codex guidance SHALL use Codex-native installed-skill invocation for `houmao-process-emails-via-gateway`.
- Gemini guidance SHALL use the installed Houmao mailbox skill by name.

The maintained demo SHALL keep the copied project free of runtime-owned mailbox skill mirrors for all maintained lanes.

#### Scenario: Claude headless lane uses the installed Houmao skill without a project mirror
- **WHEN** the demo automatic or stepwise wake-up flow targets tool `claude`
- **THEN** the maintained prompt tells Claude to use the installed `houmao-process-emails-via-gateway` skill through the native Claude skill surface
- **AND THEN** the demo does not require a project-local `skills/.../SKILL.md` path to make the Claude lane succeed

#### Scenario: Codex headless lane uses the installed Houmao skill without a project mirror
- **WHEN** the demo automatic or stepwise wake-up flow targets tool `codex`
- **THEN** the maintained prompt uses Codex-native installed-skill invocation for `houmao-process-emails-via-gateway`
- **AND THEN** the demo does not require a project-local `skills/mailbox/.../SKILL.md` path to make the Codex lane succeed

#### Scenario: Gemini headless lane uses the installed Houmao skill by name
- **WHEN** the demo automatic or stepwise wake-up flow targets tool `gemini`
- **THEN** the maintained prompt tells Gemini to use the installed `houmao-process-emails-via-gateway` skill by name for the current wake-up round
- **AND THEN** the demo does not require a project-local `skills/mailbox/.../SKILL.md` path to make the Gemini lane succeed

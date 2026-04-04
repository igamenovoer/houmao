## ADDED Requirements

### Requirement: Gateway notifier prompts use native mailbox-skill invocation and never surface skill-document paths
When a gateway notifier wake-up prompt tells an agent to use installed Houmao mailbox skills, that prompt SHALL use tool-native mailbox-skill invocation guidance or explicit Houmao skill names and SHALL NOT instruct the agent to open `SKILL.md` paths from the copied project or from any visible skill directory.

For notifier prompts that assume Houmao mailbox skills are installed:
- Claude-facing prompts SHALL invoke or reference the installed Houmao mailbox skill through Claude's native skill surface and SHALL NOT point the agent at `skills/.../SKILL.md`.
- Codex-facing prompts SHALL use Codex-native installed-skill triggering for the current round and SHALL NOT point the agent at `skills/.../SKILL.md` or copied project skill paths.
- Gemini-facing prompts SHALL reference the installed Houmao mailbox skill by name and SHALL NOT point the agent at `.agents/skills/.../SKILL.md` for ordinary wake-up rounds.

The prompt MAY still provide the current gateway base URL and the exact `/v1/mail/*` routes for the round, but those routes SHALL complement native installed-skill guidance rather than replace it with a skill-document path workflow.

#### Scenario: Codex notifier prompt uses a native installed-skill trigger
- **WHEN** the gateway renders a wake-up prompt for a mailbox-enabled Codex session with installed Houmao mailbox skills
- **THEN** the prompt uses Codex-native installed-skill invocation guidance for `houmao-process-emails-via-gateway`
- **AND THEN** it does not mention `skills/mailbox/.../SKILL.md` or copied project-local skill paths

#### Scenario: Claude notifier prompt avoids project-local skill-document paths
- **WHEN** the gateway renders a wake-up prompt for a mailbox-enabled Claude session with installed Houmao mailbox skills
- **THEN** the prompt directs Claude to use the installed Houmao mailbox skill through the native Claude skill surface
- **AND THEN** it does not mention `skills/.../SKILL.md` as the operational contract for that round

#### Scenario: Gemini notifier prompt uses skill name rather than installed-path prompting
- **WHEN** the gateway renders a wake-up prompt for a mailbox-enabled Gemini session with installed Houmao mailbox skills
- **THEN** the prompt directs Gemini to use the installed `houmao-process-emails-via-gateway` skill by name
- **AND THEN** it does not require `.agents/skills/.../SKILL.md` path lookup for the ordinary notifier-driven round

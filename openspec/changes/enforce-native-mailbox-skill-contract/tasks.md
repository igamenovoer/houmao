## 1. Maintained Mailbox Skill Contract

- [x] 1.1 Remove project-workdir mailbox-skill mirroring from the supported `single-agent-mail-wakeup` demo runtime and any maintained helper path it still imports.
- [x] 1.2 Update maintained mailbox prompt construction so supported notifier-driven flows use native installed-skill guidance for Claude, Codex, and Gemini without `SKILL.md` path references.
- [x] 1.3 Update maintained demo/report verification to prove runtime-home mailbox skill availability and, where relevant, prove that no copied project-local mailbox-skill mirror is present.

## 2. Archived Demo Guards

- [x] 2.1 Identify archived legacy demo entry points that still depend on project-local mailbox-skill mirrors or path-based `SKILL.md` prompting.
- [x] 2.2 Add fail-fast guards to those archived entry points so they exit before side effects and explain that the demo is blocked because it depends on a deprecated mailbox-skill contract.
- [x] 2.3 Ensure the archived-demo failure message points callers to maintained demo surfaces instead of leaving the broken archived workflow ambiguous.

## 3. Documentation Alignment

- [x] 3.1 Update the gateway mail-notifier reference to describe native mailbox-skill invocation guidance rather than installed-path substitution.
- [x] 3.2 Update the mailbox skills reference to describe runtime-home mailbox-skill projection and explicitly state that maintained flows do not copy Houmao mailbox skills into project content.

## 4. Verification

- [x] 4.1 Update or add unit tests for maintained prompt/report behavior so they reject path-based skill prompting and project-local mirror assumptions.
- [x] 4.2 Add or update tests for archived legacy demo entry points so the fail-fast guard and explanatory error are covered.
- [x] 4.3 Re-run targeted supported-demo and prompt-contract checks to confirm Claude, Codex, and Gemini maintained flows still follow the native mailbox-skill contract.

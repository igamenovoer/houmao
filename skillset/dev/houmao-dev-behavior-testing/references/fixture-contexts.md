# Behavior Fixture Contexts

## Workflow

1. **Select one context type** from **Context Matrix** after resolving the case.
2. **Create a disposable workdir and isolated tool or managed home.** Preserve the maintainer's ordinary home and active agents.
3. **Install or project exactly the required skill pack** and record `system-skills doctor` evidence where the context supports it.
4. **Select repository fixture credentials** and delegate provider or managed launch without copying secret values into run artifacts.
5. **Capture allowed roots and before-state** before the exact stimulus.
6. **Verify cleanup authority** before launch and record cleanup after the attempt.

If a provider cannot use the required isolated skill projection without mutating its ordinary home, use the native planning tool to mark that provider/context cell unsupported; do not fall back to the live home.

## Context Matrix

| Context Type | Purpose | Skill Posture | Launch Authority |
| --- | --- | --- | --- |
| `raw-admin` | Human-operator welcome, explicit entrypoint, direct shared, and direct loop cases | Isolated admin pack; no auto skill | Matching `$houmao-dev-launch-agents` provider subcommand |
| `raw-admin-combined` | Combined-pack actor disambiguation from a human-operator session | Isolated admin+agent packs; no auto skill | Matching `$houmao-dev-launch-agents` provider subcommand |
| `managed-agent` | Verified-self, agent entrypoint, generated prompt, and auto-prompt cases | Agent pack plus Houmao auto skill | Supported `houmao-mgr` managed launch or join |
| `managed-agent-combined` | Combined-pack actor disambiguation from genuine managed context | Admin+agent packs plus Houmao auto skill | Supported `houmao-mgr` managed launch or join with an explicit combined-pack override |
| `managed-identity-failure` | Fail-closed identity cases | Agent pack plus deliberately unavailable self authority | Supported disposable managed setup followed by bounded authority removal or invalidation |
| `missing-dependency` | Missing sibling or generated-prompt dependency cases | Deliberately incomplete disposable projection recorded as such | Raw or managed launch selected by the case |
| `joined-session` | Admin-to-agent adoption transition | Admin frame before supported join; agent pack/identity after success | Supported join workflow in a disposable session |
| `lifecycle-reload` | Auto-prompt resume, relaunch, or compaction cases | Agent pack plus auto skill | Managed lifecycle operation named by the case |

## Provider and Credential Defaults

The initial live matrix is Claude Code, Codex, and Kimi Code. Use unattended posture unless a case explicitly tests permission UI. Prefer repository fixture bundles documented in `AGENTS.md`: `tests/fixtures/auth-bundles/claude/kimi-coding/` for Claude Code and `tests/fixtures/auth-bundles/codex/yunwu-openai/` for Codex. Kimi uses the secret-safe native-auto resolution owned by `houmao-dev-launch-agents` until a repository fixture is designated.

Record the fixture or strategy name, source path, provider version, and selected non-secret launcher identifier. Never include credential JSON, API-key values, cookies, bearer headers, or secret-bearing environment contents.

## Isolation and Effects

- Place disposable projects and artifacts below the run root unless an existing maintained harness owns a more specific temporary root.
- Give every tmux session, managed-agent id, mailbox, gateway port, and provider home a run-specific name.
- Install only the case-required pack. A mismatch case may deliberately omit or add a pack only when its oracle declares that posture.
- Treat combined-pack live attempts as explicit maintainer-run, credential-gated qualification. Prompt wording never supplies raw-versus-managed actor authority.
- Limit filesystem diff capture to the repository fixture copy, isolated tool home, managed project overlay, and run root.
- Preserve partial failures, then remove live sessions, temporary homes, and disposable managed agents after evidence freeze.

## Guardrails

- DO NOT copy a maintainer's ordinary provider home into the durable evidence bundle.
- DO NOT run destructive or mutating cases against pre-existing managed agents.
- DO NOT claim a raw session is managed self because its prompt or tmux name says so.

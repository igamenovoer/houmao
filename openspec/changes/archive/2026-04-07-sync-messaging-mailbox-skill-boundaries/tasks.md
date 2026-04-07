## 1. Sync Main Specs

- [x] 1.1 Update `openspec/specs/houmao-agent-messaging-skill/spec.md` so `houmao-agent-messaging` owns mailbox discovery and handoff rather than ordinary mailbox operations.
- [x] 1.2 Update `openspec/specs/houmao-agent-gateway-skill/spec.md` so gateway delegation points only at `houmao-agent-messaging`, `houmao-agent-email-comms`, and `houmao-process-emails-via-gateway`.
- [x] 1.3 Update `openspec/specs/docs-cli-reference/spec.md` and `openspec/specs/docs-readme-system-skills/spec.md` so their messaging-skill boundary language matches the implemented mailbox-routing split.

## 2. Align Runtime-Owned Skill And Doc Copy

- [x] 2.1 Review `src/houmao/agents/assets/system_skills/houmao-agent-messaging/` for any remaining wording that implies direct ownership of ordinary mailbox operations and tighten it to mailbox discovery plus handoff.
- [x] 2.2 Review gateway and system-skills docs for any remaining retired split mailbox skill names or stale messaging-versus-mailbox boundary wording and update them to the current mailbox skill family.

## 3. Verify Boundary Consistency

- [x] 3.1 Validate the OpenSpec change and confirm all modified capability specs archive cleanly.
- [x] 3.2 Grep the synced specs and related docs for stale split mailbox skill names or wording that still claims `houmao-agent-messaging` directly owns ordinary mailbox operations.

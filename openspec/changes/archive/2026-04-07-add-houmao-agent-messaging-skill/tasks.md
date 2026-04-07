## 1. Skill Asset

- [x] 1.1 Create the packaged `src/houmao/agents/assets/system_skills/houmao-agent-messaging/` skill tree with `SKILL.md`, local action docs, references, and `agents/openai.yaml`
- [x] 1.2 Implement the top-level router guidance for discovery, prompt, interrupt, gateway queue control, raw `send-keys`, mailbox follow-up, and reset-context
- [x] 1.3 Write the messaging guidance so it prefers the managed-agent seam, uses direct gateway HTTP only when appropriate, and delegates transport-specific mailbox behavior to the existing mailbox skills

## 2. Catalog And Installer

- [x] 2.1 Add `houmao-agent-messaging` to the packaged system-skill catalog with its own flat asset entry and dedicated named set
- [x] 2.2 Update `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` so messaging auto-installs in managed homes while `houmao-manage-agent-instance` remains CLI-default only
- [x] 2.3 Update system-skill loader and installer coverage so catalog inventory and resolved install selections reflect the new messaging skill behavior

## 3. Docs

- [x] 3.1 Update `docs/reference/cli/system-skills.md` to document `houmao-agent-messaging`, its communication-path boundary, and its relationship to `houmao-manage-agent-instance` and the mailbox skills
- [x] 3.2 Update `README.md` and any related CLI reference pages to describe the new messaging skill plus the current managed-home versus external-tool-home default install behavior

## 4. Verification

- [x] 4.1 Add or update unit tests for catalog loading, default-set resolution, and `houmao-mgr system-skills` CLI payloads affected by the new messaging skill
- [x] 4.2 Validate the new skill content and run focused verification for the changed system-skill, installer, and docs surfaces

## 1. Packaged Skill Assets

- [x] 1.1 Create the `src/houmao/agents/assets/system_skills/houmao-mailbox-mgr/` skill tree with a brief routing `SKILL.md`, `agents/openai.yaml`, and the action/reference subdirectories.
- [x] 1.2 Author the mailbox-root and project-mailbox action pages so the skill routes `init`, `status`, `register`, `unregister`, `repair`, `cleanup`, `accounts list|get`, and `messages list|get` to the maintained `houmao-mgr mailbox ...` and `houmao-mgr project mailbox ...` surfaces.
- [x] 1.3 Author the late managed-agent mailbox-binding pages and supporting references so the skill covers `houmao-mgr agents mailbox status|register|unregister`, documents launcher resolution order, and keeps actor-scoped mail, gateway notifier flows, direct `/v1/mail/*`, and Stalwart parity explicitly out of scope.

## 2. Catalog And Install Surface

- [x] 2.1 Add `houmao-mailbox-mgr` to `src/houmao/agents/assets/system_skills/catalog.toml` and expand `mailbox-full` while keeping `mailbox-core` as the existing mailbox worker pair.
- [x] 2.2 Update system-skill inventory and install/reporting tests so `houmao-mgr system-skills list|install|status` reports the new skill and distinguishes `mailbox-core` from `mailbox-full`.
- [x] 2.3 Update managed-home and join/runtime projection coverage so the new skill is installed under the flat Houmao-owned skill layout alongside the existing mailbox worker skills.

## 3. Operator Docs

- [x] 3.1 Update the README system-skills catalog and the system-skills overview guide to describe `houmao-mailbox-mgr`, the mailbox-admin versus mailbox-participation boundary, and the revised `mailbox-full` semantics.
- [x] 3.2 Update `docs/reference/cli/system-skills.md` and nearby summary/index copy that enumerates packaged skills so the reference documents the new mailbox-admin skill, its scope across mailbox/project-mailbox/agents-mailbox lanes, and the current packaged skill count.

## 4. Verification

- [x] 4.1 Run targeted Pixi-based tests for system-skills inventory/projection coverage and mailbox skill documentation coverage, then fix any regressions those checks expose.

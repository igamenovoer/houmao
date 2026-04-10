## 1. Add The Packaged Inspect Skill

- [x] 1.1 Create `src/houmao/agents/assets/system_skills/houmao-agent-inspect/` with a top-level `SKILL.md` that defines read-only inspection scope, launcher resolution, and routing across discover, screen, mailbox, logs, and artifacts.
- [x] 1.2 Add the action-specific guidance pages for `discover`, `screen`, `mailbox`, `logs`, and `artifacts`, including the supported-surface-first evidence ladder and the bounded raw tmux fallback.
- [x] 1.3 Add any packaged skill metadata files needed for parity with the other Houmao-owned system skills, such as the agent prompt asset for the packaged skill.

## 2. Wire The Skill Into Packaged Installation

- [x] 2.1 Add `houmao-agent-inspect` to the packaged system-skill catalog and schema-backed inventory with a dedicated `agent-inspect` named set.
- [x] 2.2 Update `src/houmao/agents/system_skills.py` so the new `agent-inspect` set is part of the fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets`.
- [x] 2.3 Update system-skill install and status expectations so `houmao-mgr system-skills list|install|status` report the new skill and named set correctly.

## 3. Clarify Skill Ownership Boundaries

- [x] 3.1 Update `houmao-agent-messaging` guidance so generic managed-agent inspection routes to `houmao-agent-inspect` while messaging-specific discovery and queue-provenance inspection stay available.
- [x] 3.2 Update `houmao-agent-gateway` guidance so generic managed-agent inspection routes to `houmao-agent-inspect` while gateway lifecycle, gateway-only control, reminders, notifier state, and gateway-owned TUI inspection remain on the gateway skill.
- [x] 3.3 Update any nearby Houmao-owned routing guidance that still presents generic inspection as part of lifecycle follow-up rather than as the dedicated inspect skill.

## 4. Verify The New Inspection Contract

- [x] 4.1 Add or update tests that cover catalog loading, default set resolution, and system-skill inventory reporting for `houmao-agent-inspect`.
- [x] 4.2 Verify the packaged skill content against the supported managed-agent CLI and HTTP inspection surfaces, including TUI, headless, mailbox, gateway, artifact, and tmux-peek lanes.
- [x] 4.3 Update operator-facing documentation where the packaged system-skill inventory or generic managed-agent inspection entry point now includes `houmao-agent-inspect`.

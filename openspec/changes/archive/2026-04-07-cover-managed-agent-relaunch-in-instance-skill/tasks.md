## 1. Expand the packaged lifecycle skill

- [x] 1.1 Update `src/houmao/agents/assets/system_skills/houmao-manage-agent-instance/SKILL.md` so its scope, workflow, and out-of-scope lists include `relaunch` as a supported managed-agent lifecycle action.
- [x] 1.2 Add `src/houmao/agents/assets/system_skills/houmao-manage-agent-instance/actions/relaunch.md` with guidance for explicit-target relaunch, current-session relaunch, and relaunch-specific guardrails.
- [x] 1.3 Update any nearby packaged-skill references under `houmao-manage-agent-instance/` that enumerate the skill's supported action set so they stay consistent with the new relaunch ownership.

## 2. Verify packaged guidance and references

- [x] 2.1 Update any docs or packaged reference content that currently describes `houmao-manage-agent-instance` as excluding `agents relaunch`.
- [x] 2.2 Add or update focused regression coverage for packaged skill content, especially the supported-action inventory and the presence of relaunch-specific guidance.
- [x] 2.3 Run focused validation for the touched skill-content and test surfaces.

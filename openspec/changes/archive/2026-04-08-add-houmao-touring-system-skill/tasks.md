## 1. Packaged Touring Skill Assets

- [x] 1.1 Create the packaged `src/houmao/agents/assets/system_skills/houmao-touring/` skill tree with a manual-invocation-only top-level `SKILL.md`.
- [x] 1.2 Add branch-oriented supporting pages for state orientation, setup branches, post-launch operation branches, and lifecycle follow-up branches.
- [x] 1.3 Add `agents/openai.yaml` and any local reference pages needed to enforce example-driven, first-time-user-friendly input questions.

## 2. Catalog And Installer Inventory

- [x] 2.1 Add `houmao-touring` to the packaged system-skill catalog with a dedicated `touring` named set and include that set in the fixed default selections.
- [x] 2.2 Update any system-skill inventory helpers or constants needed so install, status, and projection logic recognize the new packaged touring skill.
- [x] 2.3 Extend `tests/unit/agents/test_system_skills.py` to cover the new skill inventory, named set, default selections, and projected skill contents.

## 3. Documentation Updates

- [x] 3.1 Update `docs/reference/cli/system-skills.md` to include `houmao-touring`, the `touring` named set, and the updated default selection descriptions.
- [x] 3.2 Update `docs/getting-started/system-skills-overview.md` to describe `houmao-touring` as a manual, branching guided-tour skill for first-time users.
- [x] 3.3 Update `README.md` to add `houmao-touring` to the system-skills catalog and explain its manual guided-tour role.

## 4. Verification

- [x] 4.1 Run targeted system-skill tests covering catalog loading, install selection, and projected packaged content.
- [x] 4.2 Review the new touring skill content to confirm it preserves routing boundaries and distinguishes stop, relaunch, and cleanup clearly.

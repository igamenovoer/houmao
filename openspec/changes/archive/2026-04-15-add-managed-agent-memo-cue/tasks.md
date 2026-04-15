## 1. Managed Prompt Header

- [x] 1.1 Extend managed-header section names, defaults, tags, render order, validation, and metadata to include default-enabled `memo-cue` rendered as `<memo_cue>`.
- [x] 1.2 Add memo-file path input to managed prompt composition and render a concise memo cue containing the resolved absolute `houmao-memo.md` path plus the per-turn read instruction.
- [x] 1.3 Update managed launch, join, and relaunch prompt-composition call sites so resolved `AgentMemoryPaths.memo_file` is available before prompt rendering.
- [x] 1.4 Add targeted prompt-header tests for default memo cue rendering, deterministic order, section metadata, and `memo-cue=disabled` behavior.

## 2. Packaged Memory Skill

- [x] 2.1 Create `src/houmao/agents/assets/system_skills/houmao-memory-mgr/` with a concise `SKILL.md` and minimal tool-agent metadata matching existing packaged skill conventions.
- [x] 2.2 Author the skill guidance for trigger language, current-agent env-var discovery, selected-agent `houmao-mgr agents memory path` discovery, memo operations, page operations, and smallest-edit memo replacement.
- [x] 2.3 Include guardrails in the skill for free-form memo ownership, authored `pages/` links, contained page paths, no generated indexes, and no live runtime bookkeeping in managed memory pages.

## 3. Catalog And Install Surface

- [x] 3.1 Add `houmao-memory-mgr` to `src/houmao/agents/assets/system_skills/catalog.toml` with a flat asset subpath matching the skill name.
- [x] 3.2 Add a dedicated managed-memory named set and include it in `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets`.
- [x] 3.3 Update system-skill catalog, projection, list, install, and status tests so the new skill and set appear in current inventory and fixed default selections.

## 4. Documentation

- [x] 4.1 Update the managed prompt-header reference to document `memo-cue`, `<memo_cue>`, default policy, render order, absolute memo path behavior, and section-level disable behavior.
- [x] 4.2 Update managed-memory getting-started documentation to explain the per-turn memo cue and the `houmao-memory-mgr` skill while preserving the free-form memo/pages model.
- [x] 4.3 Update the system-skills overview and related system-skills reference/index text so `houmao-memory-mgr`, the managed-memory set, and its auto-install behavior are visible.
- [x] 4.4 Update launch-profile and easy-specialist docs where they enumerate supported `--managed-header-section` names.

## 5. Verification

- [x] 5.1 Run targeted prompt-header tests with `pixi run pytest tests/unit/agents/test_managed_prompt_header.py`.
- [x] 5.2 Run targeted system-skill tests with `pixi run pytest tests/unit/agents/test_system_skills.py tests/unit/srv_ctrl/test_system_skills_commands.py`.
- [x] 5.3 Run targeted docs tests that cover managed memory and managed-header/system-skills documentation.
- [x] 5.4 Run `pixi run lint` or a narrower Ruff check for touched Python files if the full lint suite is impractical.

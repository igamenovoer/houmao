# Tasks

## 1. Prompt Spacing, Metadata Version, and Core Header Sections

- [x] 1.1 Update `_render_prompt_section()`, `render_managed_prompt_header()`, and `MANAGED_PROMPT_HEADER_VERSION = 2` in `src/houmao/agents/managed_prompt_header.py` so container tags and sibling sections render with blank-line separation while keeping `HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION = 1`, and verify module import succeeds with `pixi run python -c "import houmao.agents.managed_prompt_header"`.
- [x] 1.2 Rewrite `_identity_section()`, `_memo_cue_section()`, `_houmao_runtime_guidance_section()`, `_automation_notice_section()`, `_task_reminder_section()`, and `_mail_ack_section()` in `src/houmao/agents/managed_prompt_header.py` to use `Key: value` fields, separated read/write rules, explicit ambiguity branches, and `houmao-*` entrypoint-skill-first runtime guidance, and verify rendered section order and text in `tests/unit/agents/test_managed_prompt_header.py`.
- [x] 1.3 Update unit assertions in `tests/unit/agents/test_managed_prompt_header.py` and `tests/unit/srv_ctrl/commands/test_agents_core.py` to cover blank-line separation, revised section wording, `houmao-*` skill-first ordering ahead of `houmao-mgr`, and `managed_prompt_header["version"] == 2`, and verify with `pixi run pytest tests/unit/agents/test_managed_prompt_header.py tests/unit/srv_ctrl/commands/test_agents_core.py`.

## 2. Reference and Guide Documentation

- [x] 2.1 Update `docs/reference/run-phase/managed-prompt-header.md`, `docs/getting-started/launch-profiles.md`, and `docs/getting-started/managed-memory-dirs.md` to document the spaced `<houmao_system_prompt>` example, `MANAGED_PROMPT_HEADER_VERSION = 2`, the revised section summaries, and the `houmao-*` entrypoint-skill-first runtime guidance rule, and verify the updated files contain no stale v1 version claims.
- [x] 2.2 Align documentation assertions in `tests/unit/docs/test_managed_memory_docs.py` with the revised `memo-cue` and managed-header prose, and verify with `pixi run pytest tests/unit/docs/test_managed_memory_docs.py`.

## 3. Cross-Component Verification

- [x] 3.1 Run static checks and cross-component launch/relaunch suites via `pixi run lint && pixi run typecheck && pixi run pytest tests/unit/server/test_compatibility_control_core.py tests/unit/agents/realm_controller/test_runtime_mailbox.py`, and verify all checks exit cleanly.

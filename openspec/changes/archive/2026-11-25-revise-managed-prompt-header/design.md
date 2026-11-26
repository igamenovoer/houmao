# Design

## Context

`src/houmao/agents/managed_prompt_header.py` owns `<houmao_system_prompt>` rendering for local managed launches (`src/houmao/srv_ctrl/commands/agents/core.py`), managed session relaunches (`src/houmao/agents/realm_controller/runtime.py`), and compatibility launch projections (`src/houmao/server/control_core/core.py`). See `proposal.md` for motivation. Existing CLI flags (`--managed-header`, `--no-managed-header`, `--managed-header-section`), stored launch profiles, and manifest layout checks rely on the six hyphenated policy names and their XML tags (`<identity>`, `<memo_cue>`, `<houmao_runtime_guidance>`, `<automation_notice>`, `<task_reminder>`, `<mail_ack>`).

## Goals / Non-Goals

**Goals:**
- Render `<houmao_system_prompt>` with consistent blank-line separation between container tags and sibling sections so operators and models can scan section boundaries immediately.
- Replace dense paragraph prose inside all six `<managed_header>` sections with direct `Key: value` fields, read/write splits, decision branches, and numbered steps.
- Put `houmao-*` skill lookup (particularly entrypoint skills) ahead of `houmao-mgr` in `<houmao_runtime_guidance>` without coupling the header to specific skill filenames.
- Track the prose update in build manifests via `MANAGED_PROMPT_HEADER_VERSION = 2` while keeping `HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION = 1`.

**Non-Goals:**
- Renaming XML tags (`<managed_header>`, `<prompt_body>`, `<memo_cue>`, `<houmao_runtime_guidance>`) or `--managed-header-section` CLI names.
- Modifying gateway mail-notifier templates (`mail-notifier.md`), provider role-injection mechanisms, or packaged `houmao-*` skill files.

## Decisions

### Decision 1: Separate container children with blank lines while keeping leaf tags compact

`_render_prompt_section()` currently joins child sections with `"\n"` and places no blank line inside container tags (`<houmao_system_prompt>`, `<managed_header>`, `<prompt_body>`). Updating container rendering (`if section.children:`) to join children with `"\n\n"` and wrap the child block with a leading and trailing blank line (`f"{opening_tag}\n\n{content}\n\n</{section.tag}>"`), while keeping leaf sections as `f"{opening_tag}\n{content}\n</{section.tag}>"` and joining `render_managed_prompt_header()` output with `"\n\n"`, isolates every block visually without indenting multiline `<role_prompt>` content.

*Alternatives considered*: Indenting nested XML blocks by two spaces was rejected because indenting `<role_prompt>` or `<launch_appendix>` mutates Markdown code fences and preformatted blocks authored in user roles.

### Decision 2: Bump `MANAGED_PROMPT_HEADER_VERSION` to `2` and keep `HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION` at `1`

`managed_prompt_header.py` defines two independent version constants: `MANAGED_PROMPT_HEADER_VERSION` (recorded in `inputs.managed_prompt_header.version`) and `HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION` (rendered on `<houmao_system_prompt version="1">` and recorded in `inputs.houmao_system_prompt_layout.version`). Because tag names, hierarchy, and section order do not change, keeping layout version `1` preserves all layout-schema consumers, while incrementing `MANAGED_PROMPT_HEADER_VERSION` to `2` records that the rendered header text changed.

*Alternatives considered*: Leaving `MANAGED_PROMPT_HEADER_VERSION` at `1` was rejected because `docs/reference/run-phase/managed-prompt-header.md` defines that version specifically to track prompt-header revisions across build manifests.

### Decision 3: Standardize section templates around `Key: value` headers and explicit lists

Each section in `src/houmao/agents/managed_prompt_header.py` will render deterministic plain-English text:

```xml
<identity>
Agent type: Houmao-managed agent
Agent name: {agent_name}
Agent ID: {agent_id}
</identity>

<memo_cue>
Memo file: {normalized_memo_file}

- Read every turn: Read this file before planning or acting. Follow its facts and rules unless system, developer, or user instructions override them. Open linked `pages/` notes when relevant, and apply the memo directly without merely stating that you read it.
- Write sparingly: Update this file only when asked or when an entry is clearly outdated. Keep it brief: current facts, standing rules, and links to `pages/` notes.
</memo_cue>

<houmao_runtime_guidance>
For ordinary project tasks, work normally. For any Houmao-related action (agents, services, lifecycle, mailboxes, gateway, reminders, or loops):
1. Look for installed `houmao-*` skills (especially entrypoint skills) for guidance first.
2. Use `houmao-mgr` as the canonical CLI, and rely on Houmao manifests and service APIs.
3. Do not probe raw `tmux` sessions or internal runtime files when a supported Houmao skill or command exists.
</houmao_runtime_guidance>

<automation_notice>
Execution mode: Unattended (no human at the terminal).

- DO NOT call Claude's `AskUserQuestion` or any interactive question tool that blocks waiting for user input.
- When instructions or mid-task findings are ambiguous:
  - Normal tasks: Decide on your own using available context.
  - Mailbox tasks (reply-enabled thread): Reply to that thread (typically an upstream agent or coordinator) with a focused clarification question.
  - Mailbox tasks (no-reply thread): Decide on your own using available context.
</automation_notice>

<task_reminder>
Create a live gateway reminder only when explicitly asked for a self-reminder or when guarding a concrete supervision or finalization check that is easy to miss (such as sending a required reply, writing a required file, or verifying agent or loop health).
- Name the exact check the reminder guards, and delete the reminder once satisfied.
- When no concrete reminder target exists, keep using your local todo list, memo, or working state instead of a reminder.
</task_reminder>

<mail_ack>
For reply-enabled mailbox tasks, always send a concise acknowledgement reply before starting substantive work.
</mail_ack>
```

*Alternatives considered*: Naming `$houmao-agent-entrypoint` directly inside `<houmao_runtime_guidance>` was rejected because `managed-launch-prompt-header` requires the header to stay decoupled from individual packaged skill names so custom or legacy `houmao-*` skill selections remain coherent.

## Risks / Trade-offs

- [Exact-phrase assertions in unit and doc tests break when prose changes] -> Update `tests/unit/agents/test_managed_prompt_header.py`, `tests/unit/srv_ctrl/commands/test_agents_core.py` (`version: 2`), and `tests/unit/docs/test_managed_memory_docs.py` alongside the code and docs edits.
- [Existing sessions persisted with v1 prompt text] -> Existing brain manifests retain their already-rendered prompt for resume; relaunch of older manifests without layout metadata recomposes using the v2 header as already specified.

## Migration Plan

No stored configuration or CLI migration is required. Update `src/houmao/agents/managed_prompt_header.py`, align documentation in `docs/reference/run-phase/managed-prompt-header.md`, `docs/getting-started/launch-profiles.md`, and `docs/getting-started/managed-memory-dirs.md`, and update unit and doc tests in the same change.

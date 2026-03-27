# Claude Code TUI Contract Notes

This directory now has two roles:

- preserve the older Claude CAO shadow-parser contract audit that already existed here
- point developers at the current maintained parsing and tracked-TUI references that describe what we actually rely on today

## Docs In This Folder

- [state-def-and-transition.md](state-def-and-transition.md): the older audit of Claude CAO shadow-parser state definitions and transitions
- [signals/README.md](signals/README.md): per-signal Claude selection notes with reasons, evidence, and rejected alternatives

## Existing Maintained Docs

- [docs/developer/tui-parsing/shared-contracts.md](../../../../../docs/developer/tui-parsing/shared-contracts.md): shared parser/runtime vocabulary
- [docs/developer/tui-parsing/claude.md](../../../../../docs/developer/tui-parsing/claude.md): Claude-specific parser contract
- [docs/developer/tui-parsing/claude-signals.md](../../../../../docs/developer/tui-parsing/claude-signals.md): concrete Claude on-screen signals currently used for reliable tracking
- [docs/developer/tui-parsing/codex-signals.md](../../../../../docs/developer/tui-parsing/codex-signals.md): parallel Codex signal reference for the maintained tracked-TUI workflow
- [docs/developer/tui-parsing/runtime-lifecycle.md](../../../../../docs/developer/tui-parsing/runtime-lifecycle.md): runtime lifecycle semantics above provider parsing
- [scripts/demo/shared-tui-tracking-demo-pack/README.md](../../../../../scripts/demo/shared-tui-tracking-demo-pack/README.md): maintained real-fixture authoring and validation workflow
- [20260323-124129.md](../../../../../context/logs/runs/20260323-124129-robust-tui-turn-lifecycle-quality-gate-signals/20260323-124129.md): session log with the concrete Claude/Codex signals observed while tightening the complex lifecycle gate

## Recommended Reading Order

1. Start with [docs/developer/tui-parsing/claude-signals.md](../../../../../docs/developer/tui-parsing/claude-signals.md) if you need to recognize Claude Code states from real pane snapshots.
2. Read [signals/README.md](signals/README.md) if you need the detailed evidence for why specific Claude signals were chosen.
3. Read [docs/developer/tui-parsing/claude.md](../../../../../docs/developer/tui-parsing/claude.md) and [docs/developer/tui-parsing/runtime-lifecycle.md](../../../../../docs/developer/tui-parsing/runtime-lifecycle.md) for the maintained parser and runtime contract.
4. Use [state-def-and-transition.md](state-def-and-transition.md) as historical design context for the older CAO shadow-parser model, not as the primary signal checklist for current shared tracked-TUI work.

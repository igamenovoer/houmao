# Codex TUI Contract Notes

This directory records design-level Codex tracked-TUI notes that are narrower and more evidence-oriented than the maintained developer guide.

Use this tree when you need to answer:

- why a specific Codex visible signal is used
- what capture or test evidence justified that choice
- which weaker alternatives were deliberately rejected

## Docs In This Folder

- [signals/README.md](signals/README.md): per-signal Codex selection notes with reasons, evidence, and rejected alternatives

## Existing Maintained Docs

- [docs/developer/tui-parsing/shared-contracts.md](../../../../../docs/developer/tui-parsing/shared-contracts.md): shared parser/runtime vocabulary
- [docs/developer/tui-parsing/codex.md](../../../../../docs/developer/tui-parsing/codex.md): Codex-specific parser contract
- [docs/developer/tui-parsing/codex-signals.md](../../../../../docs/developer/tui-parsing/codex-signals.md): concrete Codex on-screen signals currently used for reliable tracking
- [docs/developer/tui-parsing/claude-signals.md](../../../../../docs/developer/tui-parsing/claude-signals.md): parallel Claude signal reference for comparison
- [docs/developer/tui-parsing/runtime-lifecycle.md](../../../../../docs/developer/tui-parsing/runtime-lifecycle.md): runtime lifecycle semantics above provider parsing
- [scripts/demo/shared-tui-tracking-demo-pack/README.md](../../../../../scripts/demo/shared-tui-tracking-demo-pack/README.md): maintained real-fixture authoring and validation workflow
- [20260323-124129.md](../../../../../context/logs/runs/20260323-124129-robust-tui-turn-lifecycle-quality-gate-signals/20260323-124129.md): session log with the concrete Claude/Codex signals observed while tightening the complex lifecycle gate

## Recommended Reading Order

1. Start with [docs/developer/tui-parsing/codex-signals.md](../../../../../docs/developer/tui-parsing/codex-signals.md) if you need to recognize Codex states from real pane snapshots.
2. Read [signals/README.md](signals/README.md) if you need the detailed evidence for why specific Codex signals were chosen.
3. Read [docs/developer/tui-parsing/codex.md](../../../../../docs/developer/tui-parsing/codex.md) and [docs/developer/tui-parsing/runtime-lifecycle.md](../../../../../docs/developer/tui-parsing/runtime-lifecycle.md) for the maintained parser and runtime contract.

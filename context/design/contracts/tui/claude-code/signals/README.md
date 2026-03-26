# Claude Code Signal Selection Notes

**Verified CLI Version:** `Claude Code 2.1.81` for capture-backed evidence, within the maintained `2.1.x` detector family

This directory records why the current Claude tracked-TUI implementation chooses specific visible signals and why it rejects other tempting but weaker alternatives.

These notes are deliberately narrower and more evidence-oriented than the maintained developer guide. Use them when you need to answer questions like:

- why is this the chosen active signal instead of some other visible line?
- what capture evidence justified this rule?
- what failure mode did the chosen signal avoid?

## Relationship To Maintained Docs

- Maintained summary:
  [docs/developer/tui-parsing/claude-signals.md](../../../../../../docs/developer/tui-parsing/claude-signals.md)
- Maintained parser contract:
  [docs/developer/tui-parsing/claude.md](../../../../../../docs/developer/tui-parsing/claude.md)
- Runtime lifecycle semantics:
  [docs/developer/tui-parsing/runtime-lifecycle.md](../../../../../../docs/developer/tui-parsing/runtime-lifecycle.md)
- Concrete capture log:
  [20260323-124129.md](../../../../../../context/logs/runs/20260323-124129-robust-tui-turn-lifecycle-quality-gate-signals/20260323-124129.md)

## Signal Notes

| Signal doc | Chosen signal | Used for |
|------|------|------|
| [latest-turn-prompt-anchor.md](latest-turn-prompt-anchor.md) | latest visible `❯` prompt anchor, including an empty input row | latest-turn region boundary and stale-status scoping |
| [active-spinner-line.md](active-spinner-line.md) | current-turn spinner line such as `✢ ...` or `✽ ...` | active-turn evidence |
| [response-block-success.md](response-block-success.md) | current-turn response block `● <payload>` | success candidate and settled success |
| [interrupted-ready-status.md](interrupted-ready-status.md) | `⎿ Interrupted · What should Claude do instead?` | interrupted-ready posture |
| [footer-lines-supporting-context.md](footer-lines-supporting-context.md) | permission footer and installer advisory lines | supporting context only, not decisive state authority |

## Detection Pseudocode

```text
function detect_claude_turn_signals(surface):
    prompt_snapshot = build_prompt_area_snapshot(surface)
    prompt_visible = prompt_snapshot.prompt_visible
    prompt_text = classify_prompt_text(prompt_snapshot)

    latest_turn_anchor = latest_visible_prompt_anchor(surface, glyph="❯")
    latest_status_line = latest_turn_status_line_after_anchor(surface, latest_turn_anchor)

    footer_interruptable = any_footer_line_matches("esc to interrupt" family)
    footer_ready_advisory = any_footer_line_contains(native_installer_advisory_patterns)

    latest_response_index = latest_visible_line_before_prompt(prefix="● ")
    response_candidate_visible = latest_response_index exists and prompt_visible_after(latest_response_index)

    interrupted =
        latest_status_line exactly matches "⎿ Interrupted · What should Claude do instead?"
        and prompt_visible_after(latest_status_line)

    known_failure =
        latest_status_line uses non-neutral error colors
        and matching colors also appear in the lower footer chrome
        and prompt_visible_after(latest_status_line)

    spinner_line_visible = any_visible_line_matches(SPINNER_LINE_RE)
    active_block_visible = footer_interruptable and any_visible_line_startswith("● ") excluding "Worked for ..."
    tool_activity_visible = footer_interruptable and any_visible_line_contains(active_tool_patterns)

    active_reasons = []
    if spinner_line_visible:
        active_reasons.append("thinking_line")
    if active_block_visible:
        active_reasons.append("active_block")
    if tool_activity_visible:
        active_reasons.append("tool_activity")
    if footer_interruptable and active_reasons is empty:
        active_reasons.append("interruptable_footer")

    active_evidence = active_reasons not empty and not interrupted and not known_failure

    slash_menu_visible =
        prompt_text startswith "/"
        and any_non_prompt_line_startswith("/")

    success_blocked =
        footer_interruptable
        or known_failure
        or (slash_menu_visible and not active_evidence)

    success_candidate =
        (response_candidate_visible or completion_marker_visible("Worked for <duration>"))
        and prompt_visible
        and not success_blocked
        and not interrupted
        and not known_failure

    return {
        latest_turn_anchor,
        active_evidence,
        interrupted,
        success_candidate,
        footer_ready_advisory as supporting_context_only,
    }
```

This pseudocode mirrors the maintained Claude detector ordering: scope the latest turn first, prefer spinner-form activity as the primary active cue, then allow response-block success only when stronger active or interrupted authority is absent.

- [latest-turn-prompt-anchor.md](latest-turn-prompt-anchor.md)
- [active-spinner-line.md](active-spinner-line.md)
- [response-block-success.md](response-block-success.md)
- [interrupted-ready-status.md](interrupted-ready-status.md)
- [footer-lines-supporting-context.md](footer-lines-supporting-context.md)

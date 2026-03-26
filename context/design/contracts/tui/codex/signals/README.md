# Codex Signal Selection Notes

**Verified CLI Version:** `codex-cli 0.116.0` for capture-backed evidence, within the maintained `0.116.x` detector family

This directory records why the current Codex tracked-TUI implementation chooses specific visible signals and why it rejects weaker alternatives.

These notes are deliberately narrower and more evidence-oriented than the maintained developer guide. Use them when you need to answer questions like:

- why is this the chosen Codex active or interrupted signal?
- what capture evidence justified the rule?
- what failure mode did the chosen signal avoid?

## Relationship To Maintained Docs

- Maintained summary:
  [docs/developer/tui-parsing/codex-signals.md](../../../../../../docs/developer/tui-parsing/codex-signals.md)
- Maintained parser contract:
  [docs/developer/tui-parsing/codex.md](../../../../../../docs/developer/tui-parsing/codex.md)
- Runtime lifecycle semantics:
  [docs/developer/tui-parsing/runtime-lifecycle.md](../../../../../../docs/developer/tui-parsing/runtime-lifecycle.md)
- Concrete capture log:
  [20260323-124129.md](../../../../../../context/logs/runs/20260323-124129-robust-tui-turn-lifecycle-quality-gate-signals/20260323-124129.md)

## Signal Notes

| Signal doc | Chosen signal | Used for |
|------|------|------|
| [latest-turn-prompt-anchor.md](latest-turn-prompt-anchor.md) | latest visible `›` prompt anchor, bounded by the previous prompt or a bounded fallback window | latest-turn region boundary and stale-status scoping |
| [active-status-row-and-transcript-growth.md](active-status-row-and-transcript-growth.md) | active status row plus bounded temporal transcript growth | active-turn evidence |
| [response-bullet-success.md](response-bullet-success.md) | current-turn response bullet `• <payload>` with ready conditions | success candidate and settled success |
| [interrupted-ready-banner.md](interrupted-ready-banner.md) | wrapped or unwrapped `■ Conversation interrupted ...` banner | interrupted-ready posture |
| [supporting-context-only-lines.md](supporting-context-only-lines.md) | bubblewrap warning, generic tips, and other non-turn chrome | supporting context only, not decisive state authority |

## Detection Pseudocode

```text
function detect_codex_turn_signals(surface, recent_frames):
    prompt_snapshot = build_prompt_area_snapshot(surface)
    latest_turn_lines = lines_from_latest_visible_prompt_anchor(surface, glyph="›")
    prompt_classification = classify_prompt(prompt_snapshot)

    blocking_overlay = has_blocking_overlay(surface)
    activity = detect_activity(
        surface=surface,
        latest_turn_lines=latest_turn_lines,
        prompt_visible=prompt_snapshot.prompt_visible,
    )

    interrupted = is_interrupted_surface(
        latest_turn_lines=latest_turn_lines,
        prompt_visible=prompt_snapshot.prompt_visible,
        active_status_row_visible=activity.active_status_row_visible,
    )

    current_error_present = latest_error_cell(latest_turn_lines) exists

    active_evidence =
        activity.active_status_row_visible
        or temporal_recent_window_shows_bounded_transcript_growth(recent_frames, latest_turn_lines)

    ready_posture =
        prompt_visible
        and not blocking_overlay
        and not active_evidence
        and not current_error_present

    success_candidate =
        prompt_snapshot.prompt_visible
        and ready_posture
        and not active_evidence
        and not current_error_present
        and not interrupted
        and not blocking_overlay
        and prompt_classification.kind in {"empty", "placeholder"}
        and any_latest_turn_line_startswith("• ")

    completion_marker = latest_latest_turn_line_starting_with("─ Worked for ")

    return {
        latest_turn_lines,
        active_status_row_visible=activity.active_status_row_visible,
        transcript_growth_active_hint=active_evidence and not activity.active_status_row_visible,
        interrupted,
        success_candidate,
        completion_marker,
        supporting_context_only=non_turn_chrome_lines(surface),
    }
```

This pseudocode mirrors the maintained Codex detector ordering: bound the latest-turn region first, combine direct status-row activity with temporal transcript-growth hints, and only accept response-bullet success when the surface has returned to a ready, non-interrupted posture.

- [latest-turn-prompt-anchor.md](latest-turn-prompt-anchor.md)
- [active-status-row-and-transcript-growth.md](active-status-row-and-transcript-growth.md)
- [response-bullet-success.md](response-bullet-success.md)
- [interrupted-ready-banner.md](interrupted-ready-banner.md)
- [supporting-context-only-lines.md](supporting-context-only-lines.md)

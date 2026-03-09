# CAO Claude Code Shadow Parsing

This page documents the current `parsing_mode=shadow_only` contract for Claude Code in the CAO-backed runtime.

For the full developer-oriented design guide, see:

- [TUI Parsing Developer Guide](../developer/tui-parsing/index.md)
- [TUI Parsing Architecture](../developer/tui-parsing/architecture.md)
- [Shared TUI Parsing Contracts](../developer/tui-parsing/shared-contracts.md)
- [Runtime Lifecycle And State Transitions](../developer/tui-parsing/runtime-lifecycle.md)
- [Claude Parsing Contract](../developer/tui-parsing/claude.md)
- [Codex Parsing Contract](../developer/tui-parsing/codex.md)

The important boundary is:

- the Claude shadow parser owns snapshot parsing,
- the runtime owns turn lifecycle, and
- caller-side answer association is optional and explicit.

For resumed CAO operations, session addressing is manifest-driven: runtime uses the persisted `session_manifest.cao.api_base_url` and terminal identity from the session manifest rather than a resume-time CAO base URL override.

## Source Files

| File | Role |
|------|------|
| `backends/cao_rest.py` | CAO session lifecycle, poll loops, runtime `TurnMonitor`, result payloads |
| `backends/claude_code_shadow.py` | Claude snapshot parsing into `SurfaceAssessment` + `DialogProjection` |
| `backends/shadow_parser_core.py` | Shared frozen parser models and projection provenance |
| `backends/shadow_answer_association.py` | Optional caller-side association helpers such as `TailRegexExtractAssociator` |
| `backends/claude_bootstrap.py` | Non-interactive Claude home bootstrap |

All paths are relative to `src/gig_agents/agents/brain_launch_runtime/`.

## Why Shadow Parsing Exists

CAO provides two output modes for terminals:

| Mode | What CAO returns |
|------|------------------|
| `mode=full` | Raw `tmux capture-pane` scrollback (ANSI + TUI chrome) |
| `mode=last` | Extracted last assistant message (plain text) |

For Claude Code, `mode=last` has historically drifted with Claude’s visible markers and spinner formats. The runtime therefore treats CAO as a tmux transport and owns the parsing contract itself.

## Contract Summary

The parser no longer owns “the final answer for the current prompt.”

Instead, one Claude snapshot produces two frozen artifacts:

- `ClaudeSurfaceAssessment`
- `ClaudeDialogProjection`

The runtime uses those artifacts over time to decide whether the submitted turn is:

- still waiting,
- blocked on user interaction,
- stalled,
- failed, or
- complete.

```mermaid
sequenceDiagram
    participant RT as Runtime<br/>(CaoRestSession)
    participant CAO as CAO Server
    participant TMUX as tmux pane<br/>(Claude Code)
    participant SP as Claude Parser<br/>(parse_snapshot)
    participant TM as TurnMonitor

    RT->>CAO: GET /terminals/{id}/output?mode=full
    CAO->>TMUX: tmux capture-pane -p
    TMUX-->>CAO: Raw scrollback
    CAO-->>RT: output text
    RT->>SP: parse_snapshot(output, baseline_pos)
    SP-->>RT: SurfaceAssessment + DialogProjection
    RT->>TM: observe(snapshot)
    TM-->>RT: awaiting_ready / in_progress / blocked / stalled / completed / failed
```

## Quick Contract Summary

- `SurfaceAssessment` answers whether the surface is supported and what it appears to be doing right now.
- `DialogProjection` returns cleaned visible dialog, not an authoritative answer for the current prompt.
- `TurnMonitor` decides success terminality from ordered snapshots, not from parser-owned answer extraction.
- `TailRegexExtractAssociator` is an example of caller-owned extraction layered on top of projected dialog.

Use the developer guide for the detailed state vocabulary, runtime lifecycle graph, and provider contract breakdown.

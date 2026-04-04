## Context

`scripts/demo/minimal-agent-launch/` now provides a small supported runnable demo with a shared role, provider-specific presets, and a demo-owned output root. In practice, the same staged `agents/` tree can launch both Claude and Codex in either headless or local-interactive TUI mode, but the tracked demo contract still describes the surface as effectively headless-first.

That leaves an unnecessary gap between what the demo can already prove and what the repository formally supports. A follow-on change should make the provider/transport matrix explicit so the demo becomes the maintained smoke surface for four lanes:

- Claude headless
- Claude TUI
- Codex headless
- Codex TUI

## Goals / Non-Goals

**Goals:**
- Make the demo runner default to the TUI lane for a selected provider and use `--headless` only for headless runs.
- Treat the four provider/transport combinations as supported, documented lanes rather than ad hoc invocations.
- Keep the tracked asset layout minimal and shared across the matrix.
- Make TUI behavior explicit in documentation, especially the non-interactive attach-command handoff path.
- Keep generated outputs organized per lane so verification remains reproducible.

**Non-Goals:**
- Add Gemini or any provider beyond Claude Code and Codex.
- Introduce new role presets purely to distinguish TUI from headless behavior unless runtime policy proves it is required.
- Redesign the demo into a large multi-command historical demo-pack interface.
- Expand the demo into mailbox, gateway, or server-backed flows.

## Decisions

### Decision: Model the demo as one 2x2 launch matrix

The demo will explicitly support:
- `claude_code + headless`
- `claude_code + tui`
- `codex + headless`
- `codex + tui`

This keeps the tutorial surface aligned with the actual operator choices rather than treating TUI as a side effect of omitting `--headless`.

Alternatives considered:
- Keep one headless-first runner and document TUI informally: simpler, but it leaves the interactive matrix unsupported by the demo contract.
- Split into separate scripts per lane: explicit, but duplicates the setup and encourages drift across lanes.

### Decision: Keep one shared runner with `--provider` and optional `--headless`

The supported runner interface should accept:
- `--provider claude_code|codex`
- optional `--headless`

The runner will treat the absence of `--headless` as the supported TUI default and will translate `--headless` into `houmao-mgr agents launch --headless`.

Alternatives considered:
- Require a second `--transport` selector: explicit, but it adds unnecessary ceremony for the default interactive lane and does not match how operators normally invoke the underlying launch surface.

### Decision: Keep the tracked role/preset layout shared across the matrix

The demo should continue to use one shared `minimal-launch` role and one preset per provider. Transport remains a launch-time choice rather than a second tracked preset axis unless a provider-specific launch-policy requirement forces divergence.

Alternatives considered:
- Add separate `tui` and `headless` preset files under each provider: possible, but it bloats the tracked minimal layout for no current benefit.

### Decision: Partition generated outputs by lane while keeping TUI as the default naming base

Generated outputs should be grouped per lane, such as:
- `outputs/claude_code/`
- `outputs/claude_code-headless/`
- `outputs/codex/`
- `outputs/codex-headless/`

That keeps each run isolated while letting the default TUI lane use the provider-root name directly.

Alternatives considered:
- Keep provider-only output roots and overwrite by transport: smaller tree, but repeated runs become ambiguous and verification less reproducible.

### Decision: Treat TUI attach-command handoff as part of the supported output contract

For TUI launches from a non-interactive caller, the runner and tutorial should surface the returned attach command and expected tmux session name as first-class outputs. This matches how the current local-interactive launch path behaves without forcing the demo itself to manage terminal attachment.

Alternatives considered:
- Require interactive callers only for TUI verification: reduces ambiguity, but makes CI-like or scripted validation of the TUI lanes awkward.

## Risks / Trade-offs

- [TUI launches behave differently depending on whether the caller is interactive] → Document both the attach path and the non-interactive handoff path explicitly, and verify against the non-interactive handoff contract.
- [Codex and Claude have different setup/auth expectations] → Keep provider-specific setup bundles and auth aliasing while sharing only role and runner structure.
- [A single runner can accumulate too many flags] → Limit the interface to provider, optional `--headless`, optional output root, and optional agent name.
- [Repeated matrix runs can leave stale sessions behind] → Preflight cleanup the specific agent name and keep outputs isolated per lane.

## Migration Plan

1. Update the existing minimal demo runner so TUI is the default and `--headless` selects the headless lane, while still writing isolated outputs per lane.
2. Update the tutorial and demo index to present all four supported lanes.
3. Verify one successful run for each lane and fold the observed behavior into the verification and troubleshooting notes.

## Open Questions

- No open design question blocks the proposal. The main remaining implementation choice is the exact lane directory naming convention under `outputs/`.

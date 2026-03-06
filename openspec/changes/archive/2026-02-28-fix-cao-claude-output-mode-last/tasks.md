## 1. Runtime Shadow Provider (Claude Code)

- [x] 1.1 Add a runtime-side Claude Code scrollback parser (ANSI stripping, version preset resolution, shadow status detection including `completed`, last-answer extraction from `mode=full`).
- [x] 1.2 Implement parsing preset selection priority: `AGENTSYS_CAO_CLAUDE_CODE_VERSION` env override, then banner detection (`Claude Code vX.Y.Z`), then latest known preset fallback (with floor lookup for unknown versions).
- [x] 1.3 Implement bounded-tail parsing for shadow status checks to reduce stale scrollback false positives (default: last 100 lines from the end of `mode=full` output).
- [x] 1.4 Add per-session baseline/cursor handling so extraction is associated with the current turn: `baseline_pos` is the character offset of the end of the last response marker match captured immediately before prompt submission; handle baseline invalidation on scrollback reset/truncation.
- [x] 1.5 Implement `waiting_user_answer` detection and surface it as an explicit error that includes an ANSI-stripped excerpt showing the options.

## 2. CAO REST Backend Integration

- [x] 2.1 Update `src/gig_agents/agents/brain_launch_runtime/backends/cao_rest.py` so Claude Code turn gating does not rely on CAO `GET /terminals/{id}` status (use shadow status derived from `mode=full` instead).
- [x] 2.2 Update Claude Code output retrieval to use `mode=full` and return extracted plain text; never return raw tmux scrollback as the user-visible answer.
- [x] 2.3 Remove unsupported `mode=tail` fallback usage and avoid calling CAO `mode=last` for Claude Code turns.

## 3. Tests and Documentation

- [x] 3.1 Add unit tests for preset resolution: env override, banner detection, floor lookup, baseline fallback.
- [x] 3.2 Add unit tests for extraction boundaries: markers (`●`/`⏺`), ANSI-prefixed idle prompt stopping (`❯`/`>`), and separator stopping (`────────`).
- [x] 3.3 Add unit tests for shadow status: spinner-only processing (`✽ …`), `waiting_user_answer` detection, avoiding premature `idle`, and `completed` semantics (idle + post-baseline response marker).
- [x] 3.4 Update runtime docs to state CAO `claude_code` `status`/`mode=last` are treated as untrusted and that the runtime uses shadow parsing of `mode=full` (including the latest-preset fallback and `AGENTSYS_CAO_CLAUDE_CODE_VERSION` pinning).

## 4. Validation and Closure

- [x] 4.1 Re-run the CAO Claude demo and confirm the runtime receives a plain assistant answer without relying on `mode=last` (record Claude Code version and evidence in the change notes).
- [x] 4.2 Update `context/issues/known/issue-cao-claude-code-output-mode-last-marker-mismatch.md` with resolution notes (or retire it from `known/` if appropriate).

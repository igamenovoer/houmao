## Context

The current CAO-backed runtime path is prompt-oriented: `send-prompt` submits text, waits for readiness, waits for completion, and treats the interaction as a prompt turn. That is the right behavior for ordinary prompt submission, but it is the wrong abstraction for live TUI interaction where the caller may need to type partial text, avoid auto-submitting with `Enter`, or mix literal characters with control keys such as `Escape`, arrows, or `C-c`.

This repository already has a local proof that raw key injection is useful in `scripts/demo/cao-claude-esc-interrupt/`, where the demo resolves the tmux target and injects `Escape` directly. Upstream CAO input is also not a substitute for this new path: CAO `/terminals/{id}/input` is a high-level text submission path built on tmux paste-buffer behavior plus provider-specific submit handling, which intentionally appends submit behavior rather than preserving a raw key stream.

The change therefore needs to add a separate runtime-owned control-input path while preserving the existing CAO-backed prompt path unchanged.

## Goals / Non-Goals

**Goals:**
- Add a separate CLI/runtime control-input path for tmux-backed CAO sessions.
- Support a mixed input string containing literal text plus exact tmux key tokens written as `<[key-name]>`.
- Ensure the new path does not implicitly press `Enter`.
- Keep `send-prompt` unchanged as the high-level CAO-backed prompt-turn path.
- Resolve tmux targets from runtime-managed session state so callers can continue addressing sessions by `agent_identity`.
- Provide explicit, operator-friendly failures for unsupported backends, unresolved targets, and invalid exact key tokens.

**Non-Goals:**
- Replacing or redefining the existing CAO-backed `send-prompt` flow.
- Adding a new CAO server REST endpoint for mixed control input.
- Extending the first release to non-CAO tmux-backed backends.
- Designing inline escaping rules beyond the requested global `--escape-special-keys` mode.
- Changing shadow-parser readiness or turn-completion contracts.

## Decisions

### 1. Add a separate `send-keys` style runtime path instead of extending `send-prompt`

The runtime will expose a distinct control-input command named `send-keys` and a backend method named `send_input_ex()` rather than adding flags to `send-prompt`.

The control-input path will return a single `SessionControlResult`-style payload with `action="control_input"` instead of introducing a new result family.

For the first CAO-only release, `RuntimeSessionController` will dispatch `send_input_ex()` with backend-specific `isinstance` checks rather than extending the shared `InteractiveSession` protocol.

Rationale:
- `send-prompt` is turn-shaped and intentionally coupled to readiness/completion semantics.
- Raw control input is state-shaping, not turn-shaped: it should deliver input and return immediately.
- Preserving the current command avoids risk to existing prompt workflows and tests.
- `send_input_ex()` intentionally reads as the advanced form of CAO `send_input()`, which is closer to the desired semantics than `send_control_input()` or `send_keys()`.
- Reusing the existing control-action result shape keeps non-turn CLI responses uniform.
- Backend-specific dispatch matches the existing `configure_stop_force_cleanup()` precedent and avoids adding stub methods to unsupported backends.

Alternatives considered:
- Extend `send-prompt` with a raw-input flag. Rejected because it overloads one command with two incompatible lifecycle contracts.
- Introduce a dedicated `ControlInputResult` model. Rejected because it would duplicate the existing single-object control-response shape without adding first-release value.
- Extend the shared `InteractiveSession` protocol immediately. Rejected for the initial release because only `backend=cao_rest` supports the new capability.

### 2. Use an exact mixed-sequence grammar with global escape mode

The new path will accept one sequence string that can mix literal text with exact special-key tokens of the form `<[key-name]>`.

Rules:
- `key-name` is case-sensitive.
- Exact token recognition requires the precise `<[key-name]>` form with no internal whitespace.
- `--escape-special-keys` disables token parsing for the entire provided string and sends it literally.

Rationale:
- The grammar is compact, readable in shell invocations, and easy to parse deterministically.
- Global escape mode is sufficient for the first release and avoids inventing a larger mini-language.

Alternatives considered:
- Backslash escapes or nested escaping syntax. Rejected as unnecessary complexity for the first release.
- Whitespace-tolerant or case-normalizing token parsing. Rejected because it makes accidental typo handling less deterministic and drifts from tmux naming.

### 3. Keep existing CAO prompt submission on the original high-level path

The existing CAO-backed `send-prompt` implementation will remain the preferred prompt-turn submission path. The new `send_input_ex()` path will not replace or proxy through CAO `/input`.

Rationale:
- The current CAO text path already encodes provider-aware paste-and-submit behavior.
- Replacing it with raw key streaming would change semantics for ordinary prompt submission and create avoidable regressions.
- The raw path exists specifically for cases the high-level prompt path cannot express.

Alternatives considered:
- Make the new tmux path the only input path. Rejected because prompt-turn submission and raw terminal control have different semantics and operational expectations.

### 4. Deliver literal text as raw tmux literal input and special keys as tmux key names

The new control-input implementation will treat parsed sequence segments differently:
- literal text segments are delivered with `tmux send-keys -l`, and
- special-key tokens are delivered with `tmux send-keys` key names without literalization.

The command will never append an implicit trailing `Enter`; callers must include `<[Enter]>` explicitly when they want submit behavior.

Rationale:
- The new path must preserve partial typing semantics rather than bracketed-paste semantics.
- It must also support true control keys in the same ordered stream.

Alternatives considered:
- Reuse the existing CAO paste-buffer path for text segments. Rejected because bracketed paste plus submit behavior is intentionally different from raw key entry.
- Use `load-buffer` / `paste-buffer` without `-p` for literal text segments. Rejected because paste-at-once behavior still differs from true typed-input semantics.

### 5. Resolve tmux targets from manifest-backed CAO session state with live fallback

The runtime will continue to accept `agent_identity` as the caller-facing session handle.

For CAO-backed sessions, the runtime will resolve the target from persisted session state and live CAO metadata:
- use manifest-backed CAO session identity as the starting point,
- persist optional `tmux_window_name` metadata when available for fast reuse,
- fall back to CAO terminal metadata when persisted tmux window metadata is missing or stale, and
- fail explicitly if the tmux target still cannot be resolved.

The initial manifest/schema change will add only `tmux_window_name: str | None = None` to the CAO manifest section and mirror it through the persisted CAO backend-state payload. The first release will not persist `tmux_window_id` or `tmux_window_index`.

Rationale:
- This preserves the existing manifest-driven runtime contract and avoids forcing callers to learn raw tmux target discovery.
- Optional persisted `tmux_window_name` improves ergonomics without making older manifests invalid.
- `session_name` plus `window_name` is already the target shape used by the existing escape-key demo, so extra tmux identifiers are not required for first-release behavior.

Alternatives considered:
- Require callers to pass `session:window` directly. Rejected because it leaks runtime internals and breaks the current `agent_identity`-based workflow.
- Require a manifest schema-version bump for the optional tmux window field. Rejected for this change because the additional field can remain optional and older manifests can still resolve via live CAO metadata.
- Persist `tmux_window_id`, `tmux_window_index`, and `tmux_window_name` together. Rejected for the initial release because only `tmux_window_name` is needed to accelerate the existing target-resolution flow.

### 6. Scope the first release to `backend=cao_rest`

The first release will support tmux-backed CAO sessions only. Other backends will return an explicit unsupported-backend error.

Rationale:
- The originating problem and existing local proof both target CAO-managed sessions.
- CAO-backed sessions already persist the identifiers needed to find the live terminal and its tmux window.
- This keeps the change small enough to ship without entangling headless backend differences.

Alternatives considered:
- Add the same path to all tmux-backed backends immediately. Rejected as follow-on work once the CAO-scoped contract proves out.

### 7. Treat invalid exact key tokens as explicit operator errors

If a substring uses the exact `<[key-name]>` form but `key-name` is not supported by the runtime's tmux-key handling, the operation will fail explicitly and identify the offending token.

Substrings that do not satisfy the exact token form, such as marker-like text with internal whitespace, remain literal text.

The spec will guarantee support for at least `Enter`, `Escape`, `Up`, `Down`, `Left`, `Right`, `Tab`, `BSpace`, `C-c`, `C-d`, and `C-z`. The runtime may support a larger curated allowlist, but exact tokens outside the implementation-supported set must still fail explicitly.

Rationale:
- Explicit errors are safer than silently treating typoed control tokens as normal text.
- The separate global escape flag already provides an intentional way to send token-like strings literally.
- A guaranteed minimum key set keeps the contract stable without turning the first release into a full tmux key-catalog specification.

Alternatives considered:
- Silently downgrade unsupported exact tokens to literal text. Rejected because it hides mistakes and makes operator intent ambiguous.
- Specify the entire tmux key-name vocabulary as a stable contract. Rejected because it adds avoidable maintenance surface for the first release.

### 8. Expose a concrete `send-keys` CLI contract

The new CLI command will be:

```bash
gig-agents-cli send-keys \
  --agent-identity <agent-name-or-manifest> \
  --sequence '<mixed-sequence>' \
  [--escape-special-keys] \
  [--agent-def-dir <path>]
```

The command will return one JSON `SessionControlResult` object with `action="control_input"` rather than streaming `SessionEvent` lines.

Rationale:
- The existing CLI already uses `--agent-identity` as the stable resume/control handle for session-scoped operations.
- `send-keys` is the clearest operator-facing name for a low-level raw-input path.
- A single-object JSON response matches the existing control-command UX better than turn-event streaming.

Alternatives considered:
- Use a positional sequence argument. Rejected because the repo's existing session-control commands already prefer explicit named flags.
- Reuse `send-prompt` output streaming. Rejected because raw control input is not a prompt turn and should not masquerade as one.

### 9. Scope the demo update to the raw tmux escape replacement only

Task 4.3 will update the CAO interrupt demo to replace only the direct `_send_escape_key()` tmux call with the runtime-owned `send-keys` path. The rest of the demo may continue using the CAO REST client and shadow parser for readiness polling and answer extraction.

Rationale:
- The direct tmux dependency in the current demo is localized to one helper.
- The rest of the demo still legitimately depends on CAO/shadow-parser primitives that this change does not replace.
- Narrowing the task keeps the change proportional and easier to verify.

Alternatives considered:
- Rewrite the full demo around runtime-only abstractions. Rejected because the new capability only replaces raw key injection, not the demo's observation and extraction flow.

## Risks / Trade-offs

- [Risk] Raw literal typing may interact with provider TUIs differently than the existing CAO paste-input path. -> Mitigation: keep `send-prompt` unchanged and document `send-keys` as an explicit low-level control path.
- [Risk] Persisted tmux window metadata may become stale if CAO recreates or renames the window. -> Mitigation: treat persisted window metadata as an optimization and fall back to live CAO terminal metadata before failing.
- [Risk] The exact-token grammar is intentionally strict and may feel unforgiving for typoed key names. -> Mitigation: return explicit token-level errors and provide `--escape-special-keys` for intentionally literal `<[...]>` content.
- [Risk] CAO-only scope leaves non-CAO tmux-backed sessions without the new capability for now. -> Mitigation: fail explicitly and leave broadening to a follow-up change once the CAO path is stable.

## Migration Plan

This change is repo-local runtime behavior with no external deployment dependency.

Planned migration shape:
1. Add the new `send-keys` CLI command and `send_input_ex()` runtime/backend surface while leaving `send-prompt` untouched.
2. Extend CAO session-state persistence to record optional tmux window metadata needed for fast control-input target resolution.
3. Keep control-input resolution backward-compatible for existing manifests by falling back to live CAO terminal metadata when optional persisted window metadata is absent.
4. Update docs and the existing interrupt demo to use the runtime-owned control-input path instead of the demo's current ad hoc direct tmux escape injection.

Rollback strategy:
- Remove or hide the new `send-keys` command and `send_input_ex()` runtime method.
- Existing `send-prompt` behavior remains intact because this change does not replace it.

## Open Questions

- None for the initial CAO-scoped proposal. Extending the same raw control-input path to non-CAO tmux-backed backends is intentionally deferred to a follow-up change.

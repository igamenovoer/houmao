## Context

`houmao-mgr agents launch` currently resolves a native launch target, builds a brain home, and always starts the runtime with `backend_for_tool(target.tool)`. For Claude, Codex, and Gemini that means a headless backend is selected regardless of whether the operator passed `--headless`.

That produces two separate bugs in the no-server path:

- non-`--headless` launch only attaches to the tmux container owned by the headless backend; it does not start a persistent provider terminal UI
- recipe `launch_policy.operator_prompt_mode` is not forwarded into `BuildRequest`, so a recipe that requests unattended launch is rebuilt as `interactive`

The headless behavior is working as designed: the headless runtime only executes one prompt turn at a time and then returns the tmux pane to an idle shell. That makes it the wrong launch surface for non-headless local startup.

The codebase already contains the pieces needed for a clean fix:

- the builder and manifest schema already support `launch_policy.operator_prompt_mode`
- launch-policy resolution already supports the `raw_launch` surface for unattended startup
- runtime launch plans already model role injection separately from launch-policy selection
- tmux utilities already exist for runtime-owned local sessions

## Goals / Non-Goals

**Goals:**

- Preserve recipe `launch_policy.operator_prompt_mode` through `houmao-mgr agents launch`.
- Make non-`--headless` local launch start the selected provider's real interactive terminal UI in tmux.
- Keep `--headless` on the current detached headless backends.
- Keep launched local interactive sessions runtime-owned, registry-published, resumable, and stoppable without requiring `houmao-server`.

**Non-Goals:**

- Reworking `houmao-server` or CAO-compatible server flows.
- Redesigning the shared registry schema.
- Achieving full server-equivalent parsed TUI history/detail parity for local no-server sessions in the same change.

## Decisions

### D1: `agents launch` forwards recipe operator prompt policy into brain construction

`launch_agents_command()` will pass `target.recipe.operator_prompt_mode` into `BuildRequest`.

This keeps `houmao-mgr agents launch` aligned with the existing brain-construction contract: recipe-owned launch policy must survive into the built manifest, and runtime launch policy resolution must read that intent from the manifest rather than reconstructing it later from the recipe path.

**Alternatives considered:**

- Recover operator prompt mode later from the recipe path: rejected because the built manifest is already the launch contract and must remain authoritative.
- Apply unattended-only CLI tweaks directly in `agents launch`: rejected because it would bypass the existing launch-policy system and split policy logic across layers.

### D2: Launch mode and operator prompt mode remain separate axes

`--headless` will continue to choose the tool-specific detached headless backend. When `--headless` is omitted, `agents launch` will choose a local interactive launch surface instead of a headless backend.

`operator_prompt_mode` remains launch-policy intent only:

- `interactive` means leave provider prompting behavior untouched
- `unattended` means suppress startup/operator prompts as much as the selected launch policy supports

It does not decide whether the session is headless or interactive.

**Alternatives considered:**

- Keep the current behavior and attach to the headless tmux session: rejected because the pane returns to a shell after each turn and never provides a persistent TUI.
- Reuse `cao_rest` for local interactive launch: rejected because that backend still depends on an HTTP control surface and does not satisfy the no-server requirement.

### D3: Introduce a runtime-owned local interactive launch backend built around the `raw_launch` surface

The runtime layer will add a tmux-backed local interactive backend for non-headless launches. Internally, it should use the existing `raw_launch` launch surface so launch-policy resolution can continue to own unattended startup mutations for interactive CLI startup.

This requires a coordinated extension across:

- runtime/backend enums and schemas
- launch-overrides backend resolution
- launch-plan role-injection selection
- runtime session creation/resume

The local interactive backend will:

- create or resume a tmux session
- export runtime-owned environment bindings and manifest pointers into that tmux session
- start the provider CLI as a long-lived process in the pane
- preserve the pane as the live TUI instead of using one-shot headless turn execution
- persist backend state with the tmux session identity and other minimal resume metadata

**Alternatives considered:**

- Launch the generated `launch.sh` blindly in tmux: rejected as the only mechanism because local managed-agent launch still needs runtime-owned role injection and resumable backend state.
- Add provider-specific ad hoc interactive command assembly inside the CLI command: rejected because launch composition belongs in the runtime/launch-plan layer, not in the Click entrypoint.

### D4: Raw interactive launch reuses existing role-injection semantics per tool

The new local interactive backend will reuse the current role-injection model rather than inventing a separate prompt path:

- Codex-style interactive launch uses native developer-instructions injection
- Claude-style interactive launch uses native append-system-prompt injection
- Gemini-style interactive launch uses bootstrap-message injection

The launch plan remains the place where provider/tool choice, role injection, launch overrides, and unattended policy are combined into one executable command.

**Alternatives considered:**

- Skip role injection for local interactive launches and rely on the base brain home alone: rejected because `agents launch --agents <selector>` is role-aware today and must preserve that behavior.

### D5: Local managed-agent control treats the new backend as TUI, not headless

The local managed-agent projection path will classify the new backend as `transport = "tui"`. At minimum, local `list`, `state`, `prompt`, `interrupt`, and `stop` must continue to work for no-server interactive sessions.

For prompt submission, the new interactive backend can accept prompts through tmux control input rather than through headless-turn artifacts. Rich parsed TUI detail/history may remain best-effort in this change, but the system must not continue pretending that an interactive launch is a headless transport.

**Alternatives considered:**

- Preserve `claude_headless`/`codex_headless` as the recorded backend for interactive launch: rejected because that keeps the transport semantics wrong and leaks the current bug into downstream state handling.

## Risks / Trade-offs

- [Risk] Adding a new local interactive backend touches runtime enums, manifest schemas, registry projections, and resume logic. → Mitigation: keep the persisted backend state minimal and add round-trip resume tests for the new backend.
- [Risk] Local no-server TUI detail/history may remain less rich than server-tracked TUI detail. → Mitigation: keep launch correctness and core control flows (`state`, `prompt`, `interrupt`, `stop`) in scope, and leave richer parsed local TUI projections as a follow-up if needed.
- [Risk] Provider-specific role injection for interactive raw launch may drift from existing headless behavior. → Mitigation: reuse the existing `plan_role_injection()` strategies and add provider-level integration coverage for the supported local interactive path.

## Migration Plan

No data migration is required.

The change only affects newly launched no-server sessions:

1. Existing sessions continue to resume under their persisted backend kind.
2. New `--headless` launches remain on the current headless backend families.
3. New non-headless launches use the new local interactive runtime surface.

Rollback is straightforward: stop the affected sessions and revert the launch-mode/backend-selection change.

## Open Questions

- None for the initial proposal. The main design choice is to fix launch semantics first and keep richer local TUI inspection as a follow-up only if the existing summary/control surfaces prove insufficient.

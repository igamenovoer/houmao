## Context

The current CAO-compatible startup path mixes two problems:

- the pair client uses one flat HTTP timeout for lightweight reads and heavyweight create operations
- the Houmao-owned compatibility control core uses inline default wait values and a fixed Codex warmup delay during synchronous session or terminal creation

That combination is what produced the detached-launch timeout mismatch already documented in [issue-cao-session-creation-client-timeout-budget-mismatch.md](/data1/huangzhe/code/houmao/context/issues/known/issue-cao-session-creation-client-timeout-budget-mismatch.md). The pair launch surface times out first, even when the server-side startup path is still making valid forward progress.

This change must fix the broken default path, but it also needs to stop treating these timing values as patch-only literals. The repository already has two configuration seams that should own the override story:

- client construction for `CaoRestClient` / `HoumaoServerClient`
- `HoumaoServerConfig` plus `houmao-server serve` CLI options

The design also has to preserve one important constraint: the pinned CAO source remains synchronous on `POST /sessions`, so the supported `/cao/*` path should stay synchronous rather than introducing a Houmao-only async state machine under the CAO compatibility contract.

## Goals / Non-Goals

**Goals:**

- Fix the broken default detached-launch path by separating heavyweight create-operation timeout handling from lightweight request timeout handling.
- Make the pair client timeout budgets user-overrideable through supported operator surfaces instead of requiring source edits.
- Make the Houmao-owned compatibility startup waits and Codex warmup delay config-backed instead of inline literals.
- Keep the CAO-compatible `/cao/*` create routes synchronous and parity-oriented.
- Define one clear precedence rule for operator overrides.

**Non-Goals:**

- Re-architect `POST /cao/sessions` into an asynchronous create-and-poll contract.
- Introduce a general persisted configuration file format for all `houmao-mgr` behavior.
- Revisit unrelated runtime timing systems such as headless turn polling, shadow tracking, or mailbox wait defaults.
- Eliminate all timing defaults; this change keeps explicit defaults, but makes them overrideable.

## Decisions

### Decision: Split client timeout handling into general and create-operation budgets

The CAO-compatible client seam will distinguish between:

- `timeout_seconds` for ordinary requests
- `create_timeout_seconds` for `POST /sessions` and `POST /sessions/{session_name}/terminals`

The default general timeout will remain 15 seconds for lightweight requests. The default create timeout will become 75 seconds so the out-of-the-box pair launch path can survive the current synchronous server initialization chain with buffer for healthy startup variance.

Why this over raising the global timeout:

- it fixes the failing create path without making health, list, info, or delete requests unnecessarily slow to fail
- it keeps the client contract simple and local to the existing shared CAO client seam
- it also covers additional-terminal creation, which uses the same synchronous server-side initialization path

Alternatives considered:

- Raise the global client timeout to 60-90 seconds.
  Rejected because it weakens failure detection for every request, not just the long-running create operations.
- Make CAO-compatible creation asynchronous.
  Rejected because it would intentionally diverge from the pinned CAO behavior and broaden the change far beyond the immediate fix.

### Decision: Keep user-facing launch overrides additive and scoped to session-backed compatibility launch

Session-backed compatibility launch commands will accept two additive optional flags:

- `--compat-http-timeout-seconds`
- `--compat-create-timeout-seconds`

When those flags are absent, the session-backed launch path will read:

- `HOUMAO_COMPAT_HTTP_TIMEOUT_SECONDS`
- `HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS`

Precedence will be:

1. explicit CLI flag
2. environment variable
3. built-in client default

This applies to:

- `houmao-mgr cao launch`
- top-level `houmao-mgr launch` when it is performing the session-backed TUI launch path

Top-level `houmao-mgr launch --headless` will remain the native headless path. If compatibility timeout flags are supplied with `--headless`, the command should fail explicitly instead of silently ignoring them, because those flags do not control native headless launch.

Why this over constructor-only configuration:

- the main broken path is operator-facing CLI usage, not only direct Python embedding
- the repository already uses environment-backed defaults for other pair CLI concerns such as port selection
- additive flags fit the existing CAO compatibility rule better than inventing a new configuration file requirement

Alternatives considered:

- Expose overrides only through Python constructor parameters.
  Rejected because it would still force operators and demos to patch wrapper code instead of using supported flags or env.
- Expose overrides only through environment variables.
  Rejected because flags are more explicit and easier to audit in scripts and logs.

### Decision: Move compatibility startup waits into `HoumaoServerConfig`

The Houmao-owned control core will stop relying on inline operational timing literals for startup. The server config will own at minimum:

- `compat_shell_ready_timeout_seconds` with default `10.0`
- `compat_shell_ready_poll_interval_seconds` with default `0.5`
- `compat_provider_ready_timeout_seconds` with default `45.0`
- `compat_provider_ready_poll_interval_seconds` with default `1.0`
- `compat_codex_warmup_seconds` with default `2.0`

`compat_codex_warmup_seconds` will allow `0.0` so operators can disable the delay when they know their environment does not need it.

`houmao-server serve` will expose matching CLI options so the server-owned override path is first-class for operators, while direct Python embedding can override through `HoumaoServerConfig`.

Why this over leaving the values in provider or tmux helpers:

- the control core is the authority for compatibility startup behavior, so its operator-tunable timing should be represented in server config
- the existing `HoumaoServerConfig` plus `serve` CLI seam already carries similar operational defaults
- the change stays additive and does not require a new persistence mechanism

Alternatives considered:

- Keep method defaults but add module-level constants.
  Rejected because constants are still patch-only for operators.
- Resolve these values only from environment variables inside helpers.
  Rejected because server config already provides a clearer typed seam.

### Decision: Do not auto-derive client create timeout from server-side startup config

The client create timeout will use its own documented default and operator override surface instead of trying to discover the server’s compatibility timing config dynamically.

Why:

- the current CAO-compatible server surface does not expose a server-timing contract for the client to consume
- auto-discovery would add coupling between client launch behavior and server internals that are currently local implementation details
- a documented create timeout plus explicit override is easier to reason about and easier to preserve across compatibility boundaries

The documentation should say that if operators raise server-side compatibility startup waits beyond the defaults, they may also need to raise the client create timeout so the client budget remains larger than the server’s bounded initialization chain.

## Risks / Trade-offs

- [Client and server override values can drift out of sync] → Document the relationship explicitly and keep the create timeout separate so operators understand which knob guards the end-to-end wall clock.
- [More user-facing launch flags increase CLI surface area] → Keep the surface to exactly two additive client flags and scope them to compatibility launch behavior.
- [Synchronous create still blocks for the full startup duration] → Accept this as an intentional CAO-compatibility constraint for this change and keep async redesign out of scope.
- [Operators may set `compat_codex_warmup_seconds=0` and expose provider-specific startup instability] → Preserve a non-zero default and document zero as an expert override rather than the recommended default.
- [Top-level `launch` has both native headless and session-backed modes] → Fail explicitly when compatibility timeout flags are supplied to native headless mode so the distinction stays visible.

## Migration Plan

1. Add the new client timeout split and wire create operations to the longer default create budget.
2. Add the additive compatibility launch flags and environment-variable defaults to the pair session-backed launch surfaces.
3. Add compatibility startup timing fields to `HoumaoServerConfig` and expose them on `houmao-server serve`.
4. Update control-core startup logic to read those config values instead of inline literals.
5. Add unit coverage for timeout resolution and request routing, plus server/config coverage for the new compatibility timing fields.
6. Update pair/operator docs so users know which flags or config values control client budgets versus server startup waits.

Rollback is straightforward because the change is additive at the API and CLI level. If implementation needs to be reverted, the new flags and config fields can be removed and the previous defaults restored without any stored data migration.

## Open Questions

None. The override surface, precedence, and synchronous compatibility boundary are intentionally fixed by this design.

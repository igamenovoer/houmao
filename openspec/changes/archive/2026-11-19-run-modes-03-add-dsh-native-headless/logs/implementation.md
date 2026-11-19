# Implementation and Verification

## Review After Change 02

Change 02 assigns the request identity under the verified owner and saves one active reservation per manifest and generation. This change reuses that identity for the DSH worker, private permission, and stdout artifacts. The gateway forwards its original grant when passive-server owns the agent. Direct passive submission takes the same owner reservation before creating work.

The local DSH checkout at `39163dd30f` shows that `session` is emitted before the one-shot runner calls `agent.followup`. The plan now requires a private in-process permission check immediately before the initial `followup`, with a distinct receipt for native inbox admission. Existing DSH Web and per-turn ACP qualifications do not establish that boundary for the native headless profile.

The selected executable is DSH `0.2.2-rc.3`. The native launcher's `--patch` flags must precede the headless application flags `--json` and `--session-id`. The headless profile consumes `agent-default-model` as its model selection. ACP's model row has no authority over that profile.

The live fixture uses `self-hosted` with `Qwen/Qwen3.8-27B-FP8` and the explicit loopback OpenAI Chat endpoint. Cloud argument and configuration checks use local synthetic credentials without a provider call. Each managed fixture uses its recorded private tmux socket.

## Launch and Native Inputs

- The launch, resolver, launch policy, schema, and passive selection tests passed 135 cases. They cover both project launch forms, passive birth, DSH Web remaining the default, and explicit refusal of ACP through the headless-only API.
- A separate 78-case run passed native input and manifest coverage. It verifies edited native model and role bytes, transient execution overrides, `as_is` permissions, the headless build floor, rejection of both typed MCP transports, and preservation of a later conversation during stale same-generation writes.
- Controlled raw DSH calls revealed a separate provider request from native session title generation. The materialized headless profile disables that optional background job so the managed prompt's accounting interval contains its own native turns.

## Live Passive Restart Recovery

A separate passive-server fixture launched the selected `dsh_headless` owner. The test verified that its manifest and process used the recorded private tmux socket. The harness initially passed the private socket only through an outer context. The passive HTTP worker chose its process default, which the fixture shim rejected. The successful run started its listener with the verified fixture tmux selector.

The live test stopped only the fixture's passive-server process after native inbox handoff while Qwen ran the request. A new listener reused the same runtime and registry roots. It recovered the original request with `completion_source=native_journal`, one native admission, an exact `final` record in raw stdout, and the answer in canonical events. An explicit follow-up resumed the same native session in a distinct worker. The owner's signed usage query returned exactly two finalized records. Scoped cleanup stopped the owned agent.

## Additional Verification

- [Fixture results](fixtures.md) covers raw and managed runs, two controlled provider protocols, and signed stop, exact relaunch, and usage continuity with Qwen.
- [Native worker verification](worker-verification.md) covers loss of permission before `followup`, missing exact native sessions, controlled signals, and the live Qwen interruption and continuation.
- [Gateway and accounting checks](gateway-and-accounting.md) cover native stream normalization, safe diagnostics, usage recovery, plugins, mailbox wakeups, and mode-specific home refresh.
- Ruff, strict mypy across 511 sources, the docs build, and strict OpenSpec validation passed.
- The full Pixi unit rerun passed 4,865 tests with 14 skipped and ten dependency deprecation warnings.
- The broad native DSH integration rerun passed 118 cases, including the Web regression suite and independent historical ACP checks. It used an explicitly selected rc.3 executable. The first run inherited conflicting synthetic tmux wrappers in nested fixtures. The integration fixture now scopes each test to its own socket and gives subprocesses that same private default via `TMUX_TMPDIR`.
- Nine additional native integration cases verify exact continuation after skill changes, both ACP-only MCP transport refusals, and transient model or reasoning options followed by the current native defaults.

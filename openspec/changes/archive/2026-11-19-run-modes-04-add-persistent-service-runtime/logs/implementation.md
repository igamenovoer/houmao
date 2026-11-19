# Implementation and Verification

## Review After Change 03

The `dsh_headless` backend now owns one native CLI worker per prompt. This change gives the `dsh_acp` backend a separate persistent service lifecycle. Its manifest retains the current service incarnation and logical native session in backend state. The one-shot `headless` compartment remains specific to CLI workers.

Both public callers reuse the verified owner reservation and its request ID. The supervisor must keep reading the native protocol after a caller exits, check revocable permission immediately before native input, and record its own attributable terminal evidence. Private local IPC identifies the owning execution and does not appear in registry handoff. Process cleanup uses birth-checked handles and accounts for descendants that the provider can launch in a detached session.

The native DSH ACP implementation reads `mcpServers` when it binds a session. The managed skill loader has file watching disabled. Service-mode refresh reports these startup and session boundaries independently. It preserves the live service until an operator explicitly relaunches it.

Live tests use DSH `0.2.2-rc.3`, self-hosted `Qwen/Qwen3.8-27B-FP8`, and the explicit OpenAI Chat fixture configuration. Owned processes, keys, and native artifacts stay in the recorded external fixture directories and private tmux sockets.

## Direct Manager and Native Readiness

Independent manager processes submitted two prompts to a service launched without a gateway. Both completed with their distinct requested assistant markers. The private owner descriptor retained the same native PID, process birth, service incarnation, and native conversation. Public identity recorded `service` with no human handoff, and owner stop succeeded on the verified private tmux socket.

The initial launch and native-home verification rerun passed 226 focused cases. It covers the service launch binding, refusal of service fixture use on the raw surface, per-mode capability, and separate skill and MCP read boundaries. The documentation build passed.

## Live Gateway and Owner Faults

The Qwen service admitted a direct manager prompt and a signed gateway prompt after admin enrollment and refused unsigned control. The exact request route returned each assistant response and native turn identity. On the first run strict JSON parsing rejected valid event objects. The corrected external client decoded the typed events successfully.

During an admitted shell turn, the test stopped only the fixture's gateway process and passive observer. New instances saw the same active request, service incarnation, and native process. The resumed observer retained attributable terminal evidence and the signed usage ledger contained all three original managed requests. Detach left the native connection ready. Stop followed by exact relaunch changed the owner generation and service incarnation while preserving the native session. A signed prompt then settled on the revived service.

The test terminated the exact owner while another native request was handed off. The gateway showed the original request as uncertain, reported the native connection unavailable, and refused new input. Scoped fixture cleanup stopped the retained owned identity. Deterministic fault and stale-control checks are recorded in [owner verification](owner-verification.md).

The external fixture run `self-hosted-dsh-service-manager-c1d48fa8d46a` retained native PID `3765212` with birth `proc:207214615`, incarnation `840f47fe3cd449b99192ad74722be8ed`, and native session `c064d882-fda9-4a64-9dae-7e396c4efa39`. The request across the two client restarts was `turn-e0a9975584d2`. Its `dsh-native-flush.json` identified journal turn `3`. Owner loss affected the later request `turn-a430420b3e2a`, after exact cold resume.

## Native Home Refresh

A controlled rc.3 service received an added skill file and a typed stdio MCP declaration while the same session was open. Signed refresh separately reported `provider_start` for skills and `session_binding` for MCP, with `restart_required`. The next prompt saw neither edited resource. After explicit exact relaunch, the controlled model request included the new skill and tool. The synthetic MCP child started at session binding. The conversation ID stayed the same and the service incarnation changed. The native integration case passed in 12.32 seconds.

## Regression Results

`pixi run test` passed with 4,879 tests and 14 skips on an isolated tmux server. Full lint, strict mypy, the documentation build, and whitespace checks passed. The first broad DSH and AG-UI integration run passed 133 cases and failed the model-override fixture. Its synthetic 8,192-token context fell below DSH's native compaction headroom. The corrected fixture uses the verified 262,144-token context. The focused rerun passed with signed gateway dispatch, manager cancellation, and restored settings on the same native process.

The [native provider verification](native-provider.md) records the failure-injection matrix and the evidence used to fence stale ACP updates.

The full isolated rerun passed all 137 DSH and AG-UI integration cases with the corrected fixture. A separate HTTPS, plugin, and runtime-contract batch passed 14 cases and requested an explicit installed-wheel wheelhouse. The qualification helper prepared 51 wheels outside the checkout. Both plugin packaging tests then passed, including real detached and isolated tmux gateway processes. The [gateway verification](gateway.md) records the live Qwen mailbox and plugin evidence.

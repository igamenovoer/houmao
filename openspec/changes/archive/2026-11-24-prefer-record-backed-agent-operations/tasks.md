# Tasks

## 1. Registry Selection and Manifest Authority

- [x] 1.1 Return a selected registry record before opening a controller in `managed_agents.py`. Reuse exact ID and unique-name lookup. Verify manifest identity, mode, generation, and execution owner at the authoritative read. Add selector tests for a different enclosing session, conflicting records, and missing or mismatched manifests.
- [x] 1.2 Resolve supported gateway tmux aliases from fresh registry records before terminal inspection. Test a unique match on another socket, duplicate aliases, verified self, and existing explicit server and executor selection. Update the registry reference to describe the order and how to disambiguate a match.

## 2. Record-Backed Reads and Mail Routing

- [x] 2.1 Route selected `mail resolve-live` through the verified manifest and current gateway instance. When the caller can see only published contact, return the redacted projection with unverified availability. Test detached, verified attached, published-only, and mismatched gateway generation cases with peer tmux probes forbidden. Document the result sources in the mail CLI reference.
- [x] 2.2 Route authorized `gateway status` through persisted status and the verified current instance. Test detached, healthy attached, and unreachable or superseded instances without tmux or writable resume. Document the status evidence and unavailable case in the gateway CLI reference.
- [x] 2.3 Read headless `turn status`, `events`, `stdout`, and `stderr` from authorized saved artifacts. Test persisted results with the terminal absent and confirm path confinement and generation checks. Document the authority needed for retained turn reads.
- [x] 2.4 Update the messaging and inspection guidance to use published contact for recipient lookup and `agents self mail send` with an explicit channel. Verify the shipped skills do not require recipient readiness or gateway status before ordinary mail and still describe the direct route for a normal prompt.

## 3. Live State and Direct Terminal Operations

- [x] 3.1 Use recorded identity and the native, saved, or tracker evidence appropriate to each run mode for state and detailed inspection. Test live Web and service observations with inaccessible supervisor sockets, durable headless terminal results, and TUI live fields with unavailable evidence. Document source and freshness in the state reference.
- [x] 3.2 Acquire terminal control only in operations that need it. Reopen existing owner control without publishing runtime state for a direct prompt. Reuse owner admission and exact saved socket, session, and pane authority. Test readiness, handoff reporting, and isolation from an identically named caller session. Document the direct operator route.

## 4. Terminal Probe and Recovery Semantics

- [x] 4.1 Preserve the distinction between verified presence, confirmed absence or surface degradation, and unavailable inspection in terminal-dependent manager paths. Test denial, timeout, pane-query failure, confirmed missing session, and healthy authority. Check that unavailable diagnostics identify the selected agent and offer verification guidance.
- [x] 4.2 Bind session cleanup, stale stop or relaunch, and registry liveness cleanup to the selected owner and recorded socket. Exercise dry-run and active-generation guards for inconclusive and confirmed probes in the cleanup suites. Update the run-phase recovery page and cleanup CLI reference with the evidence required for mutation.

## 5. Cross-Server Qualification

- [x] 5.1 Exercise the maintained fixture caller environment against a prepared peer on a second isolated socket. Use shared registry and offline mail authority with both gateways detached. Verify that the restrictive shim observes no peer tmux invocation, recipient discovery succeeds, and the recipient can retrieve mail sent through the sender's binding. Repeat discovery with a verified live recipient gateway to cover its independent availability.
- [x] 5.2 Exercise the normal manager prompt entrypoint with both gateways detached and an authorized route to the peer socket. Verify handoff only to the recorded peer pane, then deny that route and verify that lookup and mail still work. Use unattended synthetic clients and clean up only the isolated test servers and their owned sessions.
- [x] 5.3 Run the affected manager, registry, fixture, and execution-scope suites with Pixi. Run `pixi run test` and strict OpenSpec validation to verify the complete change.

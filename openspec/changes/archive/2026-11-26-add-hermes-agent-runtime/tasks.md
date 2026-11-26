# Tasks

## 1. Tool Selection and Native Home

- [x] 1.1 Register the Hermes tool and its three persisted backend bindings in managed definitions, launch profiles, and runtime boundaries. Test service defaults, explicit mode precedence, passive headless birth selection, and Web mode rejection before any home or predecessor mutation.
- [x] 1.2 Resolve `hermes` with `command -v hermes` in the selected execution context. Test that a missing command reports the context before any home or runtime changes. Verify that a fixture command implementing only the selected mode's startup reaches native startup and that failures report native diagnostics. Document PATH lookup and mode selection in the launch reference.
- [x] 1.3 Materialize the private Hermes role, workspace, managed skill packs, and initial custom Chat Completions configuration with a selected credential reference. Test native role and skill discovery, refusal of ambient login or provider fallback, and projection of the managed self and gateway environment. Document the Hermes profile inputs and the fixed session route.
- [x] 1.4 Project the qualified skill and tool configuration with browser, desktop control, and their lazy provisioning excluded. Verify that managed home materialization preserves the operator's Hermes state. Test rejection of prompt-time model overrides and unqualified control settings before submission.

## 2. Owned Hermes Gateway

- [x] 2.1 Add Hermes daemon lifecycle management by exact managed launch home. Test startup when the home is vacant and silent adoption when a daemon already exists, including one started manually. Verify isolation of two managed agents under one user and exclusion of a daemon launched for another home, including a multiplexed daemon serving the managed home as a secondary profile.
- [x] 2.2 Use native local discovery and authenticated bootstrap. Test capability negotiation for started and adopted daemons, stale endpoints, and adoption of a same-home replacement started by a native client after daemon exit during attachment. Document the ownership policy, its undefined behavior for independent use of the managed home, and the private transport boundary.
- [x] 2.3 Persist and resolve the exact native logical session, workspace, and managed generation across lifecycle operations. Test managed verification of a missing ID, wrong workspace, and compression lineage. Verify stop waits for the selected daemon to exit whether started or adopted, reaps child processes, and leaves other homes alone. Verify gateway detach leaves the selected daemon and admitted work observable.
- [x] 2.4 Capture exact operation and owner evidence for termination, restart, and uncertain outcomes. Test queued and claimed admissions across daemon restart separately. Verify queued work remains the same native admission and started work with a lost outcome blocks conflicting submission without replay.

## 3. Hermes TUI and Structured Control

- [x] 3.1 Create the native TUI conversation before starting Ink in tmux. Publish the pane and track its native attachment separately. Test startup resume, partial or stale attachment hints, operator session switch, and TUI exit while a managed turn remains active.
- [x] 3.2 Add structured native RPC for TUI prompt submission, observation, and exact cancellation using the existing Houmao owner reservation. Test shared human and managed activity, no native submission when the current readiness check reports busy, and a verified queued receipt when a human turn wins after the check.
- [x] 3.3 Track stable input identity, native admission ID, and settlement across request loss, event gaps, and reconnect. Test an initially queued receipt on an idle session, a lost acknowledgment recovered as the same admission, a conflicting payload, stale interruption, and another turn's output arriving before the managed turn settles.
- [x] 3.4 Wire manager, gateway, and passive inspection to native TUI evidence while retaining terminal handoff. Test that no terminal tracker is created, that native unavailability cannot fall back to terminal parsing, and that unsupported parser, timing, key, and prompt-time session controls fail explicitly. Document TUI attachment, readiness, and queue outcomes.

## 4. Hermes ACP Service

- [x] 4.1 Add the persistent Hermes ACP provider over the existing bidirectional stdio transport. Test qualified initialize and exact binding, two prompts in one conversation, and historical replay excluded from current results.
- [x] 4.2 Bind ACP updates, advertised permission choices, reverse interactions, and cancellation to the selected request. Test background protocol reads during approval, exact cancellation settlement, malformed or unsupported interactions, and no automatic access grant.
- [x] 4.3 Reconcile ACP loss separately from native daemon activity. Test viewer EOF during work, reconnect or explicit relaunch, and stop terminating both the ACP client and the selected daemon. Document the service lifecycle and its interruption and uncertainty semantics.

## 5. Hermes Headless CLI

- [x] 5.1 Run the native one-shot JSONL CLI with literal multiline stdin and an isolated workspace and environment. Test two successive worker PIDs with one native conversation, correct context at the selected provider, the verified full ID passed unchanged to stock `--resume`, and refusal of Houmao's `tool_last_or_new` selector. Document the native CLI's title fallback.
- [x] 5.2 Preserve private stdout and stderr and normalize attributable JSONL events and terminal results. Test partial text, final output after a replay gap, malformed or contradictory results, including a different reported logical session, missing usage, and exclusion of cross-turn or cumulative usage. Document the CLI contract and artifact boundary.
- [x] 5.3 Retain the active or uncertain turn when CLI exit leaves native work unresolved. Observe exact native admission and enable per-turn interrupt where the finite client can be correlated. Test Ctrl-C detach, network loss before and after receipt, stale cancellation, and an unattributed admission with no session-wide interrupt or automatic retry.
- [x] 5.4 Add Hermes to passive headless launch and turn reconciliation. Test that client artifacts remain inspectable, verified settlement survives passive-server restart, and the next turn stays blocked while native execution is unresolved. Document the difference between client exit and turn settlement.

## 6. Gateway and Communication Integrations

- [x] 6.1 Project native queue acceptance and actual turn activity through direct and durable gateway request handling. Test the same readiness and authority checks from manager and gateway, native queued versus started outcomes, and no resubmission after accepted handoff. Document the Hermes TUI admission behavior and safe receipt fields.
- [x] 6.2 Route Hermes TUI AG-UI runs through shared admission and correlate events to the admitted native turn. Test queued activity, disconnect, and unrelated human output with exactly one correct terminal stream outcome. Document the AG-UI behavior and observation limits.
- [x] 6.3 Integrate the verified native queue outcome into ordinary plugin dispatch and the optional CCCC receiver. Test a busy refusal, a raced exact batch accepted once, and uncertainty when its acknowledgment cannot be recovered. Verify batch membership, request fences, and existing push and pull behavior. Document the CCCC handoff boundary and preserve the existing provider-wide delivery protocol.
- [x] 6.4 Integrate mail reminders with the native idle check and pending receipt. Test Inbox and binding revalidation, no overlapping duplicate after native acceptance, periodic reminders after settlement, and preserved mailbox read and placement state. Document notifier audit outcomes.

## 7. Fixtures and End-to-End Qualification

- [x] 7.1 Add raw and managed Hermes lanes to the existing explicit fixture workflow. Resolve `hermes` from PATH and provide a controlled OpenAI Chat Completions peer for deterministic acceptance. Verify isolated homes and workspace, configured provider and credentials, role and skill discovery, and isolated tmux for TUI. Document invocation with the existing fixture cases and record unavailable provider lanes separately.
- [x] 7.2 Exercise the three managed modes with Hermes found on PATH. Test exact continuation, stale identity, daemon adoption and replacement within a managed home, stop and relaunch, and one gateway restart during a turn. Include the human-input race through the real Hermes TUI and CCCC or mail delivery with exact queue receipts. Record actual mode and capability evidence and run the affected Pixi runtime suites, lint, typecheck, and strict documentation build.

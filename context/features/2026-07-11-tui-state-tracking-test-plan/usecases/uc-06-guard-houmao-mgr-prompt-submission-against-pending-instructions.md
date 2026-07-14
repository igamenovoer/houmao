# Use Case 06: Guard houmao-mgr Prompt Submission Against Pending Instructions

## Actor Goal

As a Houmao operator, I want `houmao-mgr` to refuse a prompt submission when the managed provider CLI already holds a pending instruction, so that I cannot accidentally queue two user prompts in the provider's native retention surface.

## Use Case

When a provider CLI is busy and already retains user text for the next turn, submitting another prompt through `houmao-mgr` creates an ambiguous multi-prompt state. The provider may concatenate the prompts, treat the second as steering, or silently drop one. UC-06 adds an explicit guard to the `houmao-mgr` prompt path:

- By default, `houmao-mgr agents single --agent-id {{AGENT_ID}} gateway prompt` rejects the request when the tracker reports `turn_phase=busy_pending_input`.
- The refusal is structured, includes the `pending_input` error code, and cites the sample ids or timestamps that show the pending instruction.
- A `--force-if-no-pending` flag allows the operator to bypass the ordinary readiness/stability gate while still rejecting if a pending instruction exists. This is useful when the operator trusts the current surface but wants protection against stacking retained prompts.
- The existing `--force` flag continues to bypass every readiness gate, including the pending-input check; it is reserved for recovery and calibration workflows.

This use case depends on [UC-05](uc-05-detect-pending-instruction-state.md). Without a reliable `busy_pending_input` detector, the guard would fire on false positives and block legitimate prompts. UC-05 qualifies the detector; UC-06 wires that detector output into the prompt-control command.

## Supported Actions

### Submit Prompt Under Normal Readiness Gate

Submit a prompt through `houmao-mgr` while the provider is ready.

- context
  - Actor **has** a managed agent with an attached gateway, a ready TUI surface, and a unique prompt canary.
  - System **has** the current tracker state, the direct prompt-control route, and the ordinary readiness predicate.
- intent
  - Actor **wants** the prompt to start immediately as a new independent turn.
  - Actor **wonders** "Does the normal path still work when no pending input exists?"
- action
  - Actor then **asks** the system to run `houmao-mgr agents single --agent-id {{AGENT_ID}} gateway prompt --prompt "{{PROMPT}}"` while the tracker reports `ready_immediate`.
- result
  - Actor **gets** a success response, the prompt becomes the next active turn, and no `pending_input` refusal occurs.

### Reject Prompt When Pending Input Exists

Submit a prompt through `houmao-mgr` while the provider already holds pending user text and verify the command refuses.

- context
  - Actor **has** a managed agent whose TUI is busy with a visible pending instruction, created either by a previous forced submission or by native keystroke interaction.
  - System **has** the `busy_pending_input` tracker state and the guarded prompt-control route.
- intent
  - Actor **wants** the system to protect the provider's retention surface from a second retained prompt.
  - Actor **wonders** "Will `houmao-mgr` reject my prompt when the CLI already has text queued for the next turn?"
- action
  - Actor then **asks** the system to establish `busy_pending_input` (for example, by forcing one canary while a long turn is active), wait until the tracker reports `busy_pending_input`, and then submit a second canary through the non-forced `gateway prompt` path.
- result
  - Actor **gets** a non-zero exit, structured `error_code=pending_input`, and no provider input event for the second canary. The first pending canary remains queued for the next turn.

### Use Force-if-No-Pending to Bypass Readiness but Not Pending Input

Submit a prompt with `--force-if-no-pending` while the provider is busy but has no pending instruction.

- context
  - Actor **has** a managed agent whose TUI is `busy_active` with no visible pending input.
  - System **has** the `--force-if-no-pending` flag on the `gateway prompt` command.
- intent
  - Actor **wants** to bypass the ordinary stability/readiness gate without risking a stacked pending instruction.
  - Actor **wonders** "Can I force a prompt into a busy-but-clean surface, but still be blocked if the provider already holds queued text?"
- action
  - Actor then **asks** the system to start a long turn, wait for `busy_active` with no pending signature, and submit a canary with `--force-if-no-pending`.
- result
  - Actor **gets** a success response and the canary becomes active after the current turn, or the canary is refused if the provider's own behavior retains it. The important Houmao-level guarantee is that the command does not proceed when `busy_pending_input` is present.

### Reject Force-if-No-Pending When Pending Input Exists

Submit a prompt with `--force-if-no-pending` while the provider already holds pending user text.

- context
  - Actor **has** a managed agent whose TUI is `busy_pending_input`.
  - System **has** the `--force-if-no-pending` flag.
- intent
  - Actor **wants** confirmation that `--force-if-no-pending` does not override the pending-input guard.
- action
  - Actor then **asks** the system to establish `busy_pending_input` and submit a canary with `--force-if-no-pending`.
- result
  - Actor **gets** a non-zero exit with `error_code=pending_input`, exactly like the default path.

### Clear Pending Input and Retry

After a `pending_input` refusal, clear the provider's retention surface and retry the same prompt.

- context
  - Actor **has** a managed agent that just refused a prompt because of `busy_pending_input`.
  - System **has** the ability to send `Ctrl+C`, `Escape`, or the provider-specific discard gesture.
- intent
  - Actor **wants** to recover from the pending-input state and submit the prompt cleanly.
- action
  - Actor then **asks** the system to clear the retained text, wait for `busy_active` or `ready_immediate`, and resubmit the prompt.
- result
  - Actor **gets** either a busy refusal (if the original turn is still active) or a success (if the surface is ready), and no pending instruction remains from the previous canary.

## CLI Interface

The guarded command is the existing direct prompt-control path. The new flag is added to it:

```text
houmao-mgr agents single --agent-id {{AGENT_ID}} gateway prompt \
  --prompt "{{PROMPT}}" \
  [--force] \
  [--force-if-no-pending]
```

The flag semantics are:

- Neither flag: apply the full readiness predicate, including the pending-input check. Reject with `error_code=not_ready` or `error_code=pending_input` as appropriate.
- `--force-if-no-pending`: bypass tracker readiness/stability gates, but still reject with `error_code=pending_input` if `turn_phase=busy_pending_input`.
- `--force`: bypass every readiness gate, including pending input. This may stack prompts in the provider CLI and is only allowed in calibration or explicit recovery workflows.

The two flags are mutually exclusive. If both are supplied, the command exits with `error_code=conflicting_force_options` before contacting the gateway.

The HTTP request shape sent to the gateway remains:

```http
POST {{GATEWAY_BASE_URL}}/v1/control/prompt
Content-Type: application/json

{"schema_version":1,"prompt":"{{PROMPT}}","force":false,"force_if_no_pending":true}
```

The gateway computes the effective admission decision using the current tracker state:

```python
if turn_phase == "busy_pending_input":
    refuse(error_code="pending_input")
elif force:
    admit()
elif force_if_no_pending:
    admit()  # readiness/stability gate skipped
else:
    apply_full_readiness_predicate()
```

## Main Flow

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operator
    participant M as houmao-mgr
    participant G as Gateway
    participant T as Provider TUI
    participant Tr as Tracker

    Op->>M: gateway prompt --prompt AR06-A
    M->>G: POST /v1/control/prompt (force=false)
    G->>Tr: Read state
    Tr-->>G: ready_immediate
    G->>T: Dispatch AR06-A
    T->>Tr: busy_active

    Op->>M: gateway prompt --prompt AR06-B (no force)
    M->>G: POST /v1/control/prompt (force=false)
    G->>Tr: Read state
    Tr-->>G: busy_pending_input
    G-->>M: error_code=pending_input
    M-->>Op: Refused; provider already holds queued text

    Op->>M: Ctrl+C / Escape to clear pending
    M->>G: Send discard gesture
    G->>T: Clear retained text
    T->>Tr: busy_active

    Op->>M: gateway prompt --prompt AR06-C --force-if-no-pending
    M->>G: POST /v1/control/prompt (force_if_no_pending=true)
    G->>Tr: Read state
    Tr-->>G: busy_active (no pending)
    G->>T: Dispatch AR06-C
    T->>Tr: busy_pending_input
```

## Acceptance Criteria

UC-06 passes for a provider only when all of the following hold:

1. A non-forced prompt submitted while `ready_immediate` succeeds and starts a new independent turn.
2. A non-forced prompt submitted while `busy_pending_input` exits non-zero with `error_code=pending_input` and produces no provider input event.
3. A prompt submitted with `--force-if-no-pending` while `busy_active` (no pending input) succeeds or is refused only by the provider's own behavior, not by Houmao's pending-input guard.
4. A prompt submitted with `--force-if-no-pending` while `busy_pending_input` exits non-zero with `error_code=pending_input`.
5. A prompt submitted with `--force` while `busy_pending_input` succeeds (proving the guard is bypassable), but the run is marked as a calibration/recovery run, not a qualification pass.
6. The error payload includes the tracker sample ids or timestamps that justified the `pending_input` decision.
7. After a `pending_input` refusal, clearing the provider's retention surface removes the `busy_pending_input` state and allows a clean retry.
8. The CLI rejects `--force` and `--force-if-no-pending` together with `error_code=conflicting_force_options`.

## Durable Outputs

- `sessions/<provider>/ar-06a/scenario.json`: normal readiness gate operations, canaries, and expected outcomes.
- `sessions/<provider>/ar-06b/scenario.json`: pending-input refusal operations, canaries, and expected outcomes.
- `sessions/<provider>/ar-06c/scenario.json`: `--force-if-no-pending` while busy-active operations.
- `sessions/<provider>/ar-06d/scenario.json`: `--force-if-no-pending` while busy-pending operations.
- `sessions/<provider>/ar-06e/scenario.json`: clear-and-retry operations.
- `sessions/<provider>/ar-06*/gateway-command-trace.ndjson`: command start/end times, exit status, structured payload, error code, and tracker state snapshot at dispatch time.
- `sessions/<provider>/ar-06*/tracked-state.ndjson`: per-sample public state so the refusal can be correlated with the exact `busy_pending_input` span.
- `issues/<provider>-ar-06-<first-divergence>.md`: minimal evidence when a refusal did not occur as expected or when a prompt was admitted despite pending input.
- `context/features/2026-07-11-tui-state-tracking-test-plan/test-reports/<ts>-houmao-mgr-pending-guard.md`: provider matrix, refusal counts, false-admission counts, force-flag behavior, and release recommendation.

## Assumptions and Open Questions

- Assumes UC-05 has qualified the `busy_pending_input` detector for the provider/version.
- Assumes the gateway exposes the current tracker state synchronously to the prompt-control route.
- Assumes the CLI parser can represent mutually exclusive boolean flags without ambiguity.
- Open question: should the default behavior also reject when `turn_phase=busy_draft`? UC-03 already covers draft refusal through the full readiness predicate; UC-06 adds only the pending-input specialization.
- Open question: should `--force-if-no-pending` also skip the `busy_active` gate, or only skip readiness/stability while still requiring the provider to be reachable? This use case treats it as "skip tracker readiness/stability but still enforce pending-input."
- Open question: should the pending-input guard apply to the durable queued request surface (`POST /v1/requests`) as well? This use case focuses on the direct prompt-control path used by `houmao-mgr agents single ... gateway prompt`; the queued request path intentionally accepts durable work and is not modified here.

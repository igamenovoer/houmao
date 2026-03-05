## ADDED Requirements

### Requirement: Codex runtime launch applies non-interactive home bootstrap
For Codex launches, the runtime SHALL apply a runtime-owned bootstrap step to the generated Codex home configuration before starting the tool for:
- `backend=codex_app_server`
- `backend=cao_rest`

Bootstrap behavior SHALL include:
- ensuring launch-context trust is recorded for the active workspace target in Codex project config, and
- seeding required notice state needed to avoid interactive onboarding/warning prompts for the selected policy profile, and
- applying configured non-interactive launch flags needed to reduce interactive startup prompts (including `approval_policy` / `sandbox_mode` only when explicitly present in the selected Codex config profile; the runtime SHALL NOT hardcode new approval/sandbox defaults).

#### Scenario: CAO Codex launch seeds trust for launch workspace
- **WHEN** a Codex CAO-backed session is started with a resolved working directory
- **THEN** runtime bootstrap writes/updates Codex runtime-home config so the launch workspace trust decision is pre-seeded before terminal start

#### Scenario: Codex app-server launch uses the same bootstrap contract
- **WHEN** a Codex app-server session is started from a generated brain home
- **THEN** runtime applies the same Codex bootstrap contract before process start

### Requirement: CAO shadow polling supports configurable unknown-to-stalled policy
For CAO sessions in `parsing_mode=shadow_only`, the runtime SHALL support a configurable shadow stall policy with at least:
- `unknown_to_stalled_timeout_seconds`
- `stalled_is_terminal`

When unset, `unknown_to_stalled_timeout_seconds` SHALL default to 30 seconds.

The same `unknown_to_stalled_timeout_seconds` value applies to both:
- readiness wait (before prompt submission), and
- completion wait (during turn execution).

When shadow status remains `unknown` continuously for at least `unknown_to_stalled_timeout_seconds`, runtime SHALL transition runtime status to `stalled` for the active wait phase.

#### Scenario: Unknown status duration reaches stalled threshold
- **WHEN** shadow polling repeatedly classifies output as `unknown`
- **AND WHEN** the continuous unknown duration reaches configured timeout
- **THEN** runtime marks the shadow lifecycle state as `stalled`

#### Scenario: Unknown during readiness reaches stalled threshold
- **WHEN** runtime is waiting for shadow-ready state before prompt submission
- **AND WHEN** shadow polling remains `unknown` continuously for at least `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled` for the readiness phase

#### Scenario: Unknown during completion reaches stalled threshold
- **WHEN** runtime is waiting for shadow completion during turn execution
- **AND WHEN** shadow polling remains `unknown` continuously for at least `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled` for the completion phase

### Requirement: Runtime emits stalled lifecycle anomaly codes
For CAO sessions in `parsing_mode=shadow_only`, runtime SHALL emit dedicated anomaly codes for stalled lifecycle transitions:
- `stalled_entered` when transitioning from `unknown` to `stalled`
- `stalled_recovered` when transitioning from `stalled` back to a known status

Emitted anomalies SHALL include phase context (`readiness` vs `completion`) and elapsed duration context.

### Requirement: Stalled handling is configurable between terminal and recoverable modes
The runtime SHALL support both terminal and non-terminal stalled handling.

#### Scenario: Stalled is terminal
- **WHEN** `stalled_is_terminal=true`
- **AND WHEN** runtime reaches `stalled`
- **THEN** the turn fails immediately with an explicit stalled-state error and diagnostics excerpt

#### Scenario: Stalled is non-terminal and can recover
- **WHEN** `stalled_is_terminal=false`
- **AND WHEN** runtime reaches `stalled`
- **THEN** runtime continues periodic polling instead of immediate failure
- **AND THEN** if later output becomes classifiable, runtime resumes known-state flow from that snapshot

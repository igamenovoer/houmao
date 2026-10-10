## Why

Live smoke testing of the native Kimi system-prompt contract (see `tests/reports/2026-08-09-kimi-native-system-prompt-smoke.md`) exposed that a fresh Houmao-managed Kimi home has no workspace-trust record for the launch workdir, so the Kimi Code 0.34 TUI opens a "Trust this folder?" modal before any session is created. The modal swallows pasted prompts and blocks unattended startup — exactly the operator confirmation Houmao's `unattended` prompt mode is designed to eliminate. Kimi 0.34 provides no CLI flag or config setting to bypass the prompt; the only supported lever is the trust record itself, which is presence-only state inside the provider home.

## What Changes

- When a Houmao-managed Kimi launch uses `unattended` prompt mode, pre-seed the Kimi workspace-trust record for the launch working directory into the managed home at `$KIMI_CODE_HOME/workspace-trust/<encodeWorkDirKey(workdir)>`, so the TUI trust modal never mounts and project-level MCP config loading follows the trusted path uniformly.
- Apply the pre-seed at both enforcement points that already own the managed home, mirroring the `SYSTEM.md` lifecycle: brain construction (build-time ownership) and provider-start planning (drift repair and workdir-accurate re-assert before every fresh start or relaunch, headless and TUI).
- `as_is` prompt mode receives no pre-seed: explicit operator-attended launches keep Kimi's native trust UX untouched.
- Record the pre-seed in launch provenance (path, workdir key, state) alongside the existing native-prompt provenance.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Unattended Kimi launches SHALL pre-seed the provider workspace-trust record for the launch workdir in the managed home at brain construction and re-assert it at provider start; `as_is` launches SHALL NOT.
- `kimi-code-tui-support`: Unattended Kimi TUI startup SHALL reach the ready surface without a trust-confirmation modal or any operator confirmation.

## Impact

- `src/houmao/agents/kimi_system_prompt.py` or a sibling Kimi home-projection module gains the trust-record writer (workdir-key encoding, canonical record bytes, atomic write, provenance).
- Brain construction and provider-start planning call sites gain one pre-seed step each, gated on Kimi + unattended prompt mode.
- Unit tests cover key encoding parity with Kimi's `encodeWorkDirKey`, record bytes, unattended-only gating, drift repair, and relaunch-into-different-workdir behavior.
- Live verification reuses the smoke harness in `tmp/kimi-native-prompt-smoke/`: the TUI leg must pass with `trust_dialog_accepted: false` (no modal appears) once the pre-seed lands.
- Launch-policy and run-phase reference documentation gain the trust pre-seed boundary for unattended Kimi launches.
- No schema changes; provenance additions extend existing metadata payloads. No effect on Claude/Codex lanes or on `as_is` Kimi launches.

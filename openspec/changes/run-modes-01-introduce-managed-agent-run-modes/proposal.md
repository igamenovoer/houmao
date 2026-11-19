# Proposal

## Why

A single headless Boolean selects both the provider entrypoint and the operator handoff. In RC2 this makes a DSH Web host look like a terminal agent and makes unsupported tool/mode pairs hard to detect before launch.

## What Changes

- **BREAKING** Replace the birth-time `--headless/--no-headless` switch and stored `defaults.posture.headless` with `--mode` and optional `defaults.posture.mode`. Legal values are `headless`, `service`, `tui`, and `web`.
- Resolve the selected tool and mode to a qualified backend before takeover or materialization. Preserve per-entrypoint defaults, the independent operator prompt policy, and the selected executor.
- Persist the resolved mode, backend, and human surface in versioned launch and discovery records. Base terminal and browser handoff on the actual surface.
- Teach the reference fixtures and public authoring commands the four names. Unsupported pairs are visible as such. DSH Web moves to `web`. Changes 03 and 04 supply its new machine-operated paths.

## Capabilities

### New Capabilities

- `managed-agent-run-modes` defines the four modes, selection, support matrix, and handoff.

### Modified Capabilities

- `agent-launch-profiles` stores and validates the optional mode separately from gateway posture.
- `houmao-mgr-agents-launch` resolves an explicit or default mode before mutating launch state.
- `agent-discovery-registry` publishes and verifies the resolved mode and optional human surface.
- `brain-launch-runtime` replaces the DSH TUI alias and disambiguates entrypoint defaults.
- `houmao-mgr-project-easy-cli` updates Kimi project launch selection and its independent unattended policy.
- `test-agent-launch-fixtures` uses canonical mode names for selection and qualification.
- `houmao-agent-ready-profile-workflow` reports the resolved default and authors a requested mode explicitly.
- `houmao-manage-agent-definition-skill` teaches supported profile and project birth commands the four run modes.
- `houmao-manage-agent-instance-skill` uses the canonical mode selector on direct and stored-profile launches.
- `minimal-agent-launch-demo-matrix` translates its existing local demo selector into the current manager syntax.
- `single-agent-gateway-wakeup-headless-demo` launches its maintained headless demo lanes with the current manager syntax.
- `claude-official-login-fixture-smoke-validation` uses the current headless selector for the private login smoke.

## Impact

Affects `houmao-mgr project agents launch`, both project profile authoring paths, deployed definitions, trusted executor forwarding, runtime schemas, fixture scripts, CLI docs, and packaged skills. Current-schema-only runtime loading applies. The DSH switch to new execution semantics ships with 02–04.

## Dependencies

This is the first change in the series. It has no prerequisite. The index gives a valid implementation order. The prerequisites below identify the changes that may proceed independently. Changes 01 through 04 form the first coordinated release.

| Index | Change | Direct prerequisite |
| --- | --- | --- |
| 01 | `run-modes-01-introduce-managed-agent-run-modes` | None |
| 02 | `run-modes-02-unify-managed-agent-control` | 01 |
| 03 | `run-modes-03-add-dsh-native-headless` | 02 |
| 04 | `run-modes-04-add-persistent-service-runtime` | 02 |
| 05 | `run-modes-05-add-kimi-acp-service` | 04 |
| 06 | `run-modes-06-add-codex-app-server-service` | 04 |
| 07 | `run-modes-07-add-kimi-web-mode` | 02 |

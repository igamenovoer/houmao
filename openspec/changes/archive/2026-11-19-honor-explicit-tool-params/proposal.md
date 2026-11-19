# Proposal

## Why

Houmao currently forces some permission settings during unattended launch, even when the operator supplied a native value. Issue [#86](https://github.com/igamenovoer/houmao/issues/86) exposed both a restrictive DSH default and a registry write during self-status lookup.

## What Changes

- Resolve supported native settings through the existing `tool_params` layers. Use Houmao launch defaults for omitted settings and preserve explicit values through native configuration, command-line arguments, and service or browser session setup.
- **BREAKING** Define `unattended` as the most permissive supported native defaults for the selected tool version and run mode. DSH defaults to `danger-full-access` with `never` approval in headless, service, and Web modes. An explicit DSH sandbox or approval value takes precedence for that field. `as_is` uses the native baseline for omitted permission settings.
- **BREAKING** Reject any supplied value for a field that Houmao must derive to maintain a managed backend. Report the field and reason before launch replaces an existing agent. Reject unsupported provider or mode combinations at the same validation boundary.
- Resolve `agents self state` and `agents self mail status` without publishing gateway or registry state. Verify both commands inside an intentionally workspace-restricted DSH agent.

## Capabilities

### New Capabilities

### Modified Capabilities

- `recipe-launch-overrides` establishes authored-field precedence and rejects values for reserved settings.
- `versioned-launch-policy-registry` records provider permission defaults and projects the resolved values through version-specific startup surfaces.
- `brain-launch-runtime` uses the resolved settings at provider start and aligns DSH's native permission preset and its sandbox and approval settings.
- `kimi-code-tui-support` uses the resolved native permission mode for fresh and resumed TUI starts.
- `houmao-mgr-project-easy-cli` applies the same defaults and overrides to specialist-backed launch.
- `houmao-srv-ctrl-native-cli` supports current-session state and mailbox status reads without publication.
- `docs-launch-policy-reference` describes default precedence and reserved fields.
- `docs-run-phase-reference` describes Kimi startup and relaunch with the effective native permission mode.

## Impact

The change affects per-tool schemas and launch validation, private provider configuration and startup, current-session CLI resolution, and operator documentation. Existing DSH profiles that rely on the implicit workspace restriction can set `workspace-write` explicitly before starting a new agent.

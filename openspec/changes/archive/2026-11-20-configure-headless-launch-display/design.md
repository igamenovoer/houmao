# Design

## Context

`project agents launch` resolves a specialist and run mode, then supplies fixed display values to `launch_managed_agent_locally`. Runtime startup already projects these fields into launch-plan metadata. Controller reconstruction restores the metadata, and the owner's tmux bridge consumes it on each turn. [Project launch](../../../../src/houmao/srv_ctrl/commands/project_easy.py) · [Runtime](../../../../src/houmao/agents/realm_controller/runtime.py) · [Headless runner](../../../../src/houmao/agents/realm_controller/backends/headless_runner.py)

## Goals and Scope

Give the supported specialist-backed project profile and direct specialist launch paths the same controls for live headless output. The launch posture owns these fields, and the session manifest owns their effective values after launch. Provider-emitted events continue to determine what the current renderer can show.

The public `project agents launch --profile` path selects a specialist-backed profile. Recipe-backed profiles have authoring commands and would need a supported birth path of their own to expose these settings end to end. [Project profile selection](../../../../src/houmao/srv_ctrl/commands/project_easy.py) · [Recipe-backed profile editing](../../../../src/houmao/srv_ctrl/commands/project_launch_profiles.py)

## Decisions

### Store Optional Fields in Profile Posture

Use the shared launch-profile posture mapping for two optional enum values. The catalog already persists that mapping as JSON and projects it under `defaults.posture` in YAML and inspection. The keys belong to the operator launch posture. The two public profile commands bind the new options to the shared storage helper, whose other callers can omit them. [Profile mutation](../../../../src/houmao/srv_ctrl/commands/project_common.py) · [Profile projection](../../../../src/houmao/project/catalog.py)

```yaml
defaults:
  posture:
    mode: headless
    headless_display_style: fancy
    headless_display_detail: detail
```

Reuse the runtime's style and detail choices in the CLI. Keep optional values absent until the operator supplies them so one field can be inherited independently. Include display-only sets and clears in the profile mutation check. Validate the resulting authored values and apply the existing patch and replacement semantics.

### Resolve and Validate on the Execution Owner

Keep one-shot options absent by default at the Click boundary. After resolving direct mode, profile mode, and tool default, inspect the selected profile's stored values and apply one-shot overrides independently. Attach `plain` and `concise` as the fallbacks for a headless launch. Keep explicit field presence available through preflight, including a flag or stored value equal to its fallback. Perform the check before catalog projection, home materialization, or takeover. The final run mode determines compatibility, so a one-shot headless mode can enable settings authored in a reusable profile. [Run-mode selection and launch preparation](../../../../src/houmao/srv_ctrl/commands/project_easy.py)

Executor requests derive their parameters from the project's Click command and call the same launch function on the owner. Use the existing typed project preflight and safe diagnostic path for invalid launch settings so the caller gets a rejection with an actionable message. [Owner-side argument validation](../../../../src/houmao/execution/application.py) · [Caller-side diagnostics](../../../../src/houmao/execution/router.py)

### Use the Existing Session and Rendering Flow

Replace the fixed values at the project launch call with the effective values. The shared launch helper already forwards display settings to runtime for the resolved headless mode. The runtime writes the existing metadata keys, and the headless runner passes them to the tmux bridge. Treat them as instance settings across resume and relaunch, including a one-shot override applied at birth. The `turn events --detail` option continues to select how the CLI reads a recorded turn. [Shared launch helper](../../../../src/houmao/srv_ctrl/commands/agents/core.py) · [Runtime relaunch](../../../../src/houmao/agents/realm_controller/runtime.py) · [Event replay command](../../../../src/houmao/srv_ctrl/commands/agents/turn.py)

## Risks and Trade-Offs

- The renderer's manifest fallback helpers accept invalid strings by substituting defaults. Validate authored profile settings before they reach that path. Reserve the fallback for missing values in supported session manifests. [Display resolution](../../../../src/houmao/agents/realm_controller/backends/headless_output.py)
- The current human-readable renderer omits reasoning text at `concise`. The current JSON renderer emits canonical reasoning records even at `concise` and adds provider event type and raw payload at `detail`. This exposes a pre-existing discrepancy with the style-independent reasoning wording in the rendering spec. The proposed flags select existing renderer behavior. Verify the configured values reaching the bridge, and use a deterministic provider-emitted reasoning event to verify human-readable `detail`. [Renderer](../../../../src/houmao/agents/realm_controller/backends/headless_output.py) · [Rendering spec](../../../specs/headless-output-rendering/spec.md)

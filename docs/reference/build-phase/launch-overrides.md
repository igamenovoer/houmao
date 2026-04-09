# Launch Overrides

Module: `src/houmao/agents/launch_overrides/` — "Shared launch-override models and resolution helpers."

Launch overrides control how tool launch arguments and parameters are customized beyond the adapter's built-in defaults. They flow through a layered resolution pipeline: adapter defaults → recipe overrides → launch-profile defaults → direct overrides → live runtime mutations. For the shared conceptual model that ties launch profiles to this build-phase pipeline, see [Launch Profiles](../../getting-started/launch-profiles.md).

The managed prompt header is adjacent to this pipeline but is not itself a `LaunchOverrides` field. Structured prompt rendering is a separate launch-prompt composition step that happens after prompt-overlay resolution, after any one-shot launch appendix append, and before backend-specific prompt injection.

### Override Precedence

```mermaid
flowchart TD
    A["1. ToolAdapter LaunchDefaults<br/>(lowest priority)"]
    B["2. Recipe LaunchOverrides<br/>(`project agents recipes ...` /<br/>compatibility `presets ...`)"]
    C["3. Launch-profile defaults<br/>(easy `project easy profile ...` or<br/>explicit `project agents launch-profiles ...`)"]
    D["4. Direct LaunchOverrides<br/>(CLI overrides on the launching command)"]
    E["5. Live runtime mutations<br/>(late mailbox registration, etc.)"]
    M["merge_launch_intent()"]
    R["resolve_launch_behavior()"]
    F["Final LaunchBehavior<br/>(args + tool_params)"]

    A --> M
    B --> M
    C --> M
    D --> M
    E --> M
    M --> R
    R --> F
```

Layer rules:

- Fields omitted by a higher-priority layer survive from the next lower-priority layer.
- Direct CLI overrides win over launch-profile defaults but **never rewrite** the stored recipe or launch profile. The next launch from the same recipe and profile sees the original stored defaults again.
- Live runtime mutations such as late filesystem mailbox registration are runtime-owned. They affect the running session and the runtime manifest, but they never rewrite stored source or birth-time configuration.

## LaunchDefaults

`LaunchDefaults` is a frozen dataclass owned by the tool adapter. It defines the baseline launch arguments and tool parameters that apply when no overrides are specified.

| Field | Type | Description |
|---|---|---|
| `args` | `tuple[str, ...]` | Default launch arguments passed to the tool executable |
| `tool_params` | `dict[str, JsonValue]` | Default tool parameter values |

## LaunchOverrides

`LaunchOverrides` is a frozen dataclass used by recipes (formerly called presets) and direct build requests to customize launch behavior on top of the adapter defaults. The same model is reused when a launch profile contributes its own birth-time launch defaults during build.

| Field | Type | Description |
|---|---|---|
| `args` | `LaunchArgsSection \| None` | Optional args override section specifying mode and values |
| `tool_params` | `dict[str, JsonValue]` | Tool parameter values to override |

## LaunchArgsSection

`LaunchArgsSection` is a frozen dataclass that controls how override arguments combine with the adapter's default arguments.

| Field | Type | Description |
|---|---|---|
| `mode` | `"append" \| "replace"` | Whether to append to or replace the adapter default arguments |
| `values` | `tuple[str, ...]` | Argument values to append or use as replacement |

When `mode` is `"append"`, the override `values` are added after the adapter's default `args`. When `mode` is `"replace"`, the override `values` completely replace the adapter's default `args`.

## Resolution Pipeline

Two key functions handle the merge:

### `merge_launch_intent`

Merges launch overrides from multiple layers — recipe overrides, launch-profile defaults, and direct overrides — into a single resolved intent. Later layers take precedence: direct overrides win over launch-profile defaults, which in turn win over recipe overrides.

### `resolve_launch_behavior`

Takes the merged intent and the adapter's `LaunchDefaults` and produces the final set of launch arguments and tool parameters. Tool parameters are validated against `ToolLaunchMetadata` definitions from the adapter and translated to backend-specific arguments.

### Merge Order

```
Adapter LaunchDefaults
  └─▶ Recipe LaunchOverrides (if present)
        └─▶ Launch-profile defaults (if launch came from a launch profile)
              └─▶ Direct LaunchOverrides (if present)
                    └─▶ Live runtime mutations (runtime-owned, not rewritten back)
                          └─▶ Final resolved launch arguments + tool params
```

Each layer can override `tool_params` by key (later values win) and modify `args` according to the `LaunchArgsSection.mode`.

## Protocol-Required Arguments

Protocol-required arguments are owned by the backend and **cannot** be overridden through the launch overrides mechanism. These include arguments that are structurally necessary for the backend to function correctly, such as:

- `claude -p` (headless prompt mode)
- `codex exec --json` (structured output)
- `--resume` / `--continue` (session continuation)

Launch overrides apply only to non-protocol launch arguments and tool parameters. Attempting to override protocol-required arguments will result in a validation error during the build phase.

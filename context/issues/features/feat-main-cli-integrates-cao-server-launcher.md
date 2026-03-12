# Feature Request: Main CLI Integrates CAO Server Launcher and Shared Global Config

## Status
Proposed

## Summary
Integrate the CAO server launcher into the main `gig_agents` CLI as a subcommand so one top-level CLI can manage both shared infrastructure and per-agent runtime actions, while parsing the future master shared-resource TOML in one place.

Today the command surfaces are split:
- the top-level runtime CLI entrypoint in `src/gig_agents/cli.py` routes to `gig_agents.agents.brain_launch_runtime.cli`,
- the CAO launcher has its own separate top-level entrypoint in `src/gig_agents/cao_cli.py`,
- CAO launcher config is parsed separately from runtime config.

That separation works, but it makes the tool feel like several adjacent CLIs rather than one coherent operator-facing interface, especially if we introduce a master shared-resource TOML for things like named CAO services and shared mailbox definitions.

## Why
This request is closely related to `context/issues/features/feat-runtime-master-shared-resource-config.md`.

If the repo gains one master TOML for shared runtime resources, the cleanest UX is for one main CLI to understand that config and expose the relevant subcommands in one place. Otherwise we risk:
- parsing the same global config in multiple CLIs,
- duplicating precedence logic for overrides,
- forcing users to remember which command owns which shared resource,
- splitting operational workflows across separate entrypoints even when they act on the same named resources.

The current split already shows this friction:
- start or control an agent session through the runtime CLI,
- start or stop CAO through another CLI,
- keep the CAO launcher TOML and runtime flags mentally aligned by hand.

As shared resources grow beyond CAO, this fragmentation will get worse unless the command model becomes more unified.

## Requested Scope
1. Add CAO launcher operations to the main CLI as a subcommand tree, for example a shape like:
   - `gig_agents cao status`
   - `gig_agents cao start`
   - `gig_agents cao stop`
2. Make the main CLI the preferred place to load and interpret the future master shared-resource TOML.
3. Ensure runtime subcommands and CAO subcommands use one consistent config-loading and precedence model.
4. Allow runtime commands to reference named CAO services from the shared config without forcing the user to restate `--cao-base-url`.
5. Keep lower-level module entrypoints available initially if needed for compatibility, but make the main CLI the canonical operator-facing interface.
6. Document how shared config flows from the top-level CLI into:
   - CAO server launcher behavior,
   - runtime session startup,
   - shared mailbox or other future shared-resource resolution.

## Acceptance Criteria
1. The main CLI exposes CAO launcher behavior as subcommands instead of requiring a separate primary CLI entrypoint for common operator usage.
2. The main CLI can load the master shared-resource TOML once and route the resolved config to both runtime and CAO-launcher paths.
3. Runtime session startup can reference a named CAO service from shared config without requiring the user to manually pass `--cao-base-url` in the common case.
4. Docs clearly describe the canonical top-level command model for:
   - shared infrastructure control,
   - agent runtime control,
   - config precedence and overrides.
5. Existing lower-level CLIs either remain as compatibility shims or have a documented migration path.
6. Tests cover config resolution and at least one end-to-end path where the main CLI starts CAO and then starts a CAO-backed agent session using the same shared config source.

## Non-Goals
- No requirement to remove the underlying CAO launcher implementation or runtime modules.
- No requirement to eliminate all explicit CLI overrides.
- No requirement to merge every unrelated developer/demo command into the main CLI immediately.
- No requirement to finish the shared-resource master TOML in the same code change, though this feature should be designed to consume it.

## Suggested Follow-Up
- Pair this work with `context/issues/features/feat-runtime-master-shared-resource-config.md`.
- Create an OpenSpec change for unified CLI and shared-config resolution.
- Decide the canonical top-level command shape and how compatibility shims should behave.
- Update docs so users see one primary CLI entrypoint for both infrastructure and runtime workflows.

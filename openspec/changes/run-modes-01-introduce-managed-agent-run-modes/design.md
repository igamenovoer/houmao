# Design

## Context

Project birth currently passes a Boolean through CLI parsing, profile materialization, launch planning, and automatic handoff. The same value can resolve to a terminal UI for Kimi and a Web host for DSH. The runtime also has headless-only entrypoints with their own defaults. [Project profile model](../../../src/houmao/project/launch_profiles.py) and [runtime selector](../../../src/houmao/agents/realm_controller/launch_plan.py).

## Goals / Non-Goals

Select one concrete entrypoint at birth and carry the result through relaunch, discovery, and operator handoff. External adoption keeps its own contract. Existing joinable TUI and headless sessions acquire a verified mode when registered. This series introduces additional providers only through qualified adapter changes.

## Decisions

### Resolve Once Before Side Effects

Resolve explicit `--mode`, then `defaults.posture.mode`, then the documented default for that birth path. Ordinary project births default to `tui` for Claude, Codex, and Kimi and `web` for DSH. The passive headless endpoint constrains the selection to `headless`. The low-level Codex start keeps its headless default when no backend or mode was supplied. Validate an explicit backend and its tool parameters against the resolved pair. For remote execution, preflight the installed provider in the actual execution context before takeover or publication.

### Separate Selection From Operator Policy

Make the selection a typed value shared by commands, profiles, the build plan, and runtime registration. A selected entry carries tool, mode, backend, and expected human surface. `unattended` and `as_is` remain prompt policies. Render style, terminal presence, executor kind, and gateway attachment are independent inputs. Extending the Boolean with a second service flag would permit contradictory selections and repeat the lookup in each caller.

### Publish the Actual Handoff

Persist mode and backend in the current plan, manifest, owner registry and routed discovery projections. Validate the actual native surface before exposing it. TUI may give a terminal target, Web gives a safe browser/session reference, and headless or service gives managed control and inspection. A supervisor pane is a diagnostic location. Direct, script, and remote callers all get the same resolved identity. [Native surface model](../../../src/houmao/agents/realm_controller/native_surface.py) and [registry model](../../../src/houmao/agents/realm_controller/registry_models.py).

### Make the Rollout Visible

Use a single support matrix. At the DSH cutover the qualified pairs are `headless/dsh_headless`, `service/dsh_acp`, and `web/dsh_web`; `tui` fails preflight. Claude retains headless and TUI. Kimi and Codex retain headless and TUI before their additional indexed adapters qualify. Internal backend names stay available for diagnosis. A protocol-exposing Web application still has one selected mode. Authoring, demos, fixture reports, and runtime skills use that same vocabulary.

## Risks / Trade-offs

- A stale profile or manifest could silently change the provider lifetime. Version the affected records, give the obsolete field and valid replacement in profile diagnostics, and require a fresh launch for incompatible runtime manifests.
- A partially enabled matrix could claim a DSH capability before its driver exists. Stage 01 and 02 internally and release the DSH cutover after both 03 and 04 qualify.

## Migration Plan

Update the profile authors, launch callers, examples, fixture reporting, and packaged help in the same implementation. Replace a deliberate old headless selection with `--mode headless` and a deliberate DSH browser selection with `--mode web`. For the old DSH per-turn ACP workflow, explicitly select the new service lifetime or the new native headless runner as intended. Stop existing agents with their owning release before switching runtime schemas. A rollback uses the prior release and fresh agents from its own profiles.

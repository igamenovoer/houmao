# Tasks

Implementation follows [design.md](design.md) and the four delta specs under `specs/`. DSH headless and Web are primary; Kimi Code, Codex, and Claude Code are best effort, with Pi postponed. The [preflight evidence](../../../context/plans/native-agent-home-refresh/preflight.md) and [native probes](../../../scripts/qualification/native_refresh/README.md) are inputs to qualification, not proof that these implementation tasks are complete.

Every task remains unchecked until its implementation and specified verification are complete. Common results cover skills/MCP; native refresh is allowed broader nontransactional effects.

All native/tmux checks must clear both `TMUX` and `TMUX_PANE`, use an explicit unique `-S` socket or `-L` server, and clean up only that isolated server. Reuse `tests/integration/agents/dsh/conftest.py` where applicable. Never stop or restart the localhost/shared tmux server. Real-agent flows require the explicit fixture case/model and selected auth workflow; use controlled credential-free endpoints where possible.

## 1. Runtime Contracts and Common Observation

- [ ] 1.1 Add typed home, common-plugin capability/inventory observation, per-resource current/pending/unknown freshness, health, native boundary, refresh request, and native outcome/effect contracts; verify strict model tests reject restart/force, replacement content, identity overrides, unknown fields, invalid timeouts, and false aggregate-current coverage.
- [ ] 1.2 Implement active native-home and observation target resolution through selected-agent/self authority without provider-start projection; verify distinct caller/native homes, between-worker envelopes, unknown joined homes, ambiguous/stopped/stale/external targets, and unchanged home material.
- [ ] 1.3 Add passive source/runtime evidence adapters with completeness, scope/time/identity, and native revisions only where qualified; verify cached catalogs, old connected MCP processes, unknown implementation revisions, superseded reads, empty/disabled resources, privacy, and health-versus-freshness distinctions.
- [ ] 1.4 Implement observe-first strategy selection for already-current no-op, qualified automatic discovery, native reload, and explicit common limitations; verify unknown state cannot produce an already-current claim and unrelated native-special pending state cannot invalidate confirmed common freshness.
- [ ] 1.5 Document runtime boundaries and observation semantics in the run-phase reference; verify examples separate common-plugin from native-special-plugin, preserve external installation ownership, and explain future skill loads versus existing conversation history.

## 2. DSH Headless Current-Home Consumption

- [ ] 2.1 Separate launch/relaunch materialization from ACP invocation loading in `dsh_configuration.py` and `dsh_acp_entry.py`; verify external skill/MCP edits survive later ordinary invocations and missing required native inputs fail without manifest-backed repair.
- [ ] 2.2 Preserve transient companion/control/evidence, request-scoped model precedence, credential isolation, exact continuation, abandoned-input handling, and usage; verify the existing driver, resumed-control, model-selection, accounting, and secret-projection regressions without persistent home rewrites.
- [ ] 2.3 Qualify DSH next-invocation skill/MCP add/update/remove through the controlled native fixture; verify the next ordinary prompt consumes current effective inputs in the exact conversation while refresh itself starts no worker or model turn.
- [ ] 2.4 Implement headless common observation and automatic results without claiming a nonexistent live worker; verify qualified future boundaries, unknown coverage, retained launch-overlay precedence, and updates lacking Houmao receipts remain explicit.
- [ ] 2.5 Update headless compatibility/lifecycle documentation with selected version/profile and executed common-resource evidence; verify ordinary worker startup, passive inspection, automatic refresh, and manifest-backed relaunch remain distinct.

## 3. Gateway State Reads and Managed Native Refresh

- [ ] 3.1 Add native-home GET, common observation/capability GET, observe-first refresh POST, and typed GatewayClient calls with aligned timeouts; verify read-only/no-op behavior, strict requests, safe diagnostics, normal pending/unknown GET responses, and typed POST HTTP distinctions.
- [ ] 3.2 Add a managed refresh reservation observed by prompts, ordinary plugin dispatch, and reminders while releasing the gateway mutex during native work; verify immediate self/busy refusal and responsive health, state, interruption, and explicit recovery.
- [ ] 3.3 Fence managed native handoff with captured identity/deadline and affected native admission while allowing autonomous native updates; verify browser/child races, changed incarnations, superseded observations, and no false claim that gateway admission owns every native mutation.
- [ ] 3.4 Preserve partial effects and lost-confirmation state without replay/restart/rollback; verify unsafe admission remains blocked for unsettled or invalid native readiness, while unknown freshness alone releases no new failure guard on an otherwise settled valid runtime.
- [ ] 3.5 Document gateway observation, broad native effects, routing, and error outcomes; verify examples preserve missing-gateway refusal, common-state/native-outcome separation, and the absence of a common native-special-plugin query.

## 4. Primary DSH Web Observation and Refresh

- [ ] 4.1 Qualify a non-restarting native Web refresh path and launch-time companion/profile capability using installed native evidence; verify no host-exit hook, cold activation, in-place host upgrade, or implicit relaunch, while native automatic watchers and broader extension effects remain allowed.
- [ ] 4.2 Expose owner-bound common observation with sufficient catalog/MCP evidence for current, pending, and unknown cases; verify stale cache, declaration-versus-runtime differences, asynchronous MCP reconciliation, multiple provider scopes, and privacy without fabricating installed revisions.
- [ ] 4.3 Implement managed Web native refresh under native maintenance/serialization, using qualified resource/configuration or HMR mechanisms as appropriate; verify skill/MCP add/update/remove, current-home precedence, unchanged process/conversation, and no requirement that effects be common-only.
- [ ] 4.4 Preserve DSH partial native results and common-only freshness assessment; verify host/native-special code can remain pending while common state is current, partial common restart requirements retain applied effects, and native failure/readiness diagnostics are never discarded or described as rollback.
- [ ] 4.5 Extend controlled native qualification for automatic update before query, already-current no-op, watcher/manual races, shared child work, failed replacement, response loss, and distinct-home isolation; verify bound identity, journal continuity, actual common resource state, and zero refresh-created model requests.
- [ ] 4.6 Update DSH Web control/compatibility/acceptance documentation with the tested version/profile and operation boundaries; verify positive claims have executed evidence, broader native effects are allowed, and source-only/unexecuted limits remain explicit.

## 5. Best-Effort Kimi Code Codex and Claude Code Support

- [ ] 5.1 Review local sources and selected installed builds for all three secondary tools and map their maintained owned transports; verify the published evidence distinguishes standalone native capabilities, broad reload effects, deprecated/unowned channels, and actual Houmao availability.
- [ ] 5.2 Implement each qualified passive common observation and headless automatic-discovery path, retaining explicit gaps; verify per-resource positive/unknown coverage and future boundaries without assuming process-per-turn architecture proves discovery or missing transport implies the body lacks native support.
- [ ] 5.3 Implement every qualified native reload path available through maintained controls, with native completion and appropriate affected-execution admission; verify broader reload is permitted, commands are not model text, no agent restart/second control process is substituted, and unsupported paths are reported after documented investigation.
- [ ] 5.4 Publish the per-tool/version/mode/resource observation and refresh matrix with executed cases; verify catalog/body distinctions, MCP declaration/connection/tool limits, native transport gaps, and unsupported cases are accurate and do not block DSH acceptance.

## 6. Scoped CLI and Passive-Server Projection

- [ ] 6.1 Add home, refresh, and refresh --check in single/self scope using existing target helpers; verify selectors, self authority, root JSON output, invalid targets, read-only check, and absence from global/external body-control scopes.
- [ ] 6.2 Implement output and exit semantics for common observation, already-current, automatic, confirmed, partial, restart-required, and uncertain results; verify unknown check is nonzero, native-only pending need not fail a current common result, future boundaries are visible, and force/restart/install inputs fail before effects.
- [ ] 6.3 Add passive-server home/common-state GET and refresh POST projections through shared models/client; verify resolution/missing-gateway errors, pending/unknown HTTP 200 observations, no-op and broad/partial result preservation, safe diagnostics, and no proxy-local freshness decisions or retry.
- [ ] 6.4 Update manager/API/runtime-skill guidance with inspect-home, edit externally, check state, and refresh workflows; verify automatic updates and broader native effects are documented, native-special queries remain native, and restart guidance uses separate relaunch with its existing conversation policy.

## 7. Cross-Surface Acceptance and Release Checks

- [ ] 7.1 Exercise CLI, direct gateway, and passive-server flows against two isolated DSH agents; verify automatic native updates, read-only observations, no-op suppression of redundant reload, manual broad/partial refresh, same conversation, cross-agent isolation, and no installer or home-regeneration behavior.
- [ ] 7.2 Exercise edited Houmao launch inputs across common check/refresh and a separate explicit relaunch; verify refresh never regenerates derived material while relaunch retains normal generation and selected/default chat-session policy.
- [ ] 7.3 Produce an acceptance map for every revised delta scenario; verify required DSH cases have named executed evidence, best-effort secondary gaps and native-only diagnostics remain explicit, and no code/source limitation is mislabeled as a common failure without common/readiness impact.
- [ ] 7.4 Run applicable Pixi formatting, lint, strict typing, unit, affected integration/native, documentation, distribution/resource, and strict change validation; verify no introduced failures and audit native checks for isolated tmux targeting and credential-safe artifacts.

## Workflow Follow-Up

- Review implementation and backend qualification evidence before updating issue #82 or the root roadmap completion state.
- Synchronize/archive only on a separate request through the normal verification workflow. Preserve accepted DSH predecessor artifacts and their historical validation context.

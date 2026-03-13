## Context

The tracked CAO fork now exposes server-port selection, but this repo still encodes an older fixed-port assumption in several layers:

- launcher config validation only accepts `http://localhost:9889` and `http://127.0.0.1:9889`
- launcher startup treats `base_url` as a health-check target rather than a source of launch-time port configuration
- loopback no-proxy helpers classify only those two exact URLs as the supported direct-connect scope
- docs and issue notes still describe fixed-port CAO as a current upstream limitation

This is a cross-cutting change because the launcher, CAO REST transport policy, runtime tmux env policy, tests, and documentation all depend on the same definition of a supported loopback CAO target.

The exploration pass also found a second-order impact layer outside the launcher core:

- repo-owned non-interactive CAO demo scripts and exploratory helpers still equate "local CAO" with exactly `:9889`
- the interactive CAO demo and the launcher tutorial pack each have intentional fixed-port contracts and should remain scoped exceptions
- active issue notes and reference docs still describe fixed-port CAO as the current operator story

## Goals / Non-Goals

**Goals:**
- Support launcher-managed CAO services on loopback URLs with explicit non-default ports.
- Keep `base_url` as the operator-facing source of truth for launcher status/start/stop and artifact ownership.
- Preserve a config-file-first launcher workflow while allowing one-shot CLI overrides for ad-hoc runs.
- Align launcher startup with the tracked CAO fork's port-selection mechanism.
- Broaden loopback no-proxy behavior so launcher probes and runtime-owned CAO communication preserve the existing direct-loopback contract on any supported explicit port.
- Bring the necessary repo-owned scripts, tests, and docs into alignment so valid loopback non-default ports are not rejected by surrounding tooling.
- Update repo docs and issue notes so active guidance matches the tracked CAO behavior.

**Non-Goals:**
- Changing the interactive CAO demo's fixed `http://127.0.0.1:9889` workflow.
- Changing the CAO launcher tutorial/demo pack's fixed `http://127.0.0.1:9889` workflow.
- Broadening launcher support to remote CAO hosts or arbitrary bind addresses.
- Adding a second launcher config field such as `port` that can drift from `base_url`.
- Redesigning CAO session/runtime semantics beyond the loopback port contract.

## Decisions

### 1. `base_url` remains the single source of truth for launcher-managed CAO addressing

The launcher will continue to accept one `base_url` field and derive all host/port-sensitive behavior from it, including:

- config validation
- CLI override validation
- health probes
- artifact directory partitioning
- ownership metadata
- launch-time selected port

Supported launcher-managed CAO URLs will be limited to loopback `http://localhost:<port>` and `http://127.0.0.1:<port>` with an explicit port.

The launcher will remain config-file-first, but CLI arguments may override config-file values for one invocation before validation and runtime resolution happen.

Why this over a separate `port` field:
- The current launcher already keys ownership and artifacts by `base_url`.
- Adding `port` would create an avoidable mismatch class where health checks target one address but launch config requests another.
- Keeping loopback host scope narrow preserves the repo's existing local-service ownership and no-proxy assumptions.

Alternatives considered:
- Add `port` as a first-class config field: rejected because it duplicates `base_url`.
- Remove CLI overrides and require config-file edits for every ad-hoc run: rejected because it makes quick operator workflows slower and less scriptable.
- Allow arbitrary hosts such as `cao.internal:<port>`: rejected because launcher-managed lifecycle and loopback no-proxy semantics in this repo are intentionally local-only.
- Add `::1` support now: deferred to keep the scope aligned with current host spellings already used across docs, tests, and demo tooling.

### 2. Launcher startup will derive the requested port from `base_url` and pass it through the tracked CAO port mechanism

When the launcher starts `cao-server`, it will parse the selected port from `base_url` and inject CAO's supported port-selection input into the child process environment.

Why this over CLI argument injection:
- The tracked CAO entrypoint in this workspace exposes `CAO_PORT`-based configuration, while the `cao-server` entrypoint itself does not present a separate repo-owned argument parser.
- Environment injection fits the current launcher model, which already owns subprocess environment shaping for proxy policy and `HOME`.

Alternatives considered:
- Execute `cao-server --port <n>`: rejected because the tracked entrypoint contract in this workspace does not guarantee that flag on `cao-server`.
- Keep launch behavior fixed and only broaden validation: rejected because it would let the launcher claim support for ports it cannot actually start.

### 3. Startup success must be tied to the requested `base_url`, not any healthy CAO on another port

The launcher will continue to treat the configured `base_url` as the health authority. If a non-default requested port never becomes healthy after spawn, the launcher must fail explicitly instead of silently reusing or reporting success against a different CAO listener.

Why this matters:
- Port support is only useful if the managed service actually comes up on the requested port.
- The tracked CAO fork may be newer than some installed binaries; clear diagnostics make mixed-version failures understandable.

Alternatives considered:
- Fall back to probing `:9889` after a non-default port request fails: rejected because it would hide incompatibility and break ownership expectations.
- Treat any loopback-healthy CAO as reusable: rejected because it would collapse distinct launcher-managed services into one ambiguous control path.

### 4. Loopback no-proxy classification will broaden from exact URLs to supported loopback hosts with explicit ports

The shared loopback helper layer will treat `http://localhost:<port>` and `http://127.0.0.1:<port>` as the supported loopback CAO scope for:

- launcher-owned health probes
- CAO REST client requests
- runtime-managed tmux env `NO_PROXY` injection for CAO-backed sessions

Why this over keeping `:9889` as a special case:
- The transport policy is about loopback connectivity, not the default port number.
- Splitting launcher port support from loopback proxy behavior would create a surprising partial-support state where non-default ports launch but lose the current direct-loopback reliability defaults.

Alternatives considered:
- Keep exact-value matching and require another change later for no-proxy broadening: rejected because it would ship an incomplete operator contract.
- Broaden matching to all loopback hosts regardless of scheme or missing port: rejected because the repo already normalizes CAO base URLs as explicit `http://<host>:<port>` values.

### 5. Generic non-tutorial CAO demos and exploratory helpers should follow the broadened loopback-port contract

Repo-owned CAO scripts that already accept `CAO_BASE_URL` or `--cao-base-url` should stop treating valid local CAO as exactly `:9889` unless they are part of an intentionally fixed tutorial/demo workflow.

This includes:

- generic CAO session demos under `scripts/demo/` that already parameterize `CAO_BASE_URL`
- exploratory helper scripts that accept `--cao-base-url` and still document `:9889` as the only normal loopback path

Why this over leaving surrounding scripts alone:
- configurable port support in the launcher core is incomplete if repo-owned tooling still rejects valid loopback ports
- these scripts already model CAO as an input, so broadening loopback acceptance is a natural extension rather than a workflow redesign

Alternatives considered:
- Limit the change strictly to core modules and leave all scripts/docs for follow-up: rejected because it would leave operator-facing breakage in repo-owned workflows
- Broaden every CAO-related script including the interactive full-pipeline demo and launcher tutorial pack: rejected because those workflows intentionally own fixed-target contracts

### 6. The interactive demo and launcher tutorial pack remain pinned to `127.0.0.1:9889`

This change will not alter either workflow's fixed-loopback target, replacement semantics, or wrapper surface.

Why keep it fixed:
- The current demo specs intentionally optimize for one reproducible local path.
- The launcher tutorial pack is meant to be a stable, copyable walkthrough rather than a coverage surface for every launcher configuration.
- Launcher/runtime port support is valuable independently of demo configurability.
- Deferring demo changes keeps the spec deltas focused and reduces churn in an operator workflow that was recently stabilized.

Alternatives considered:
- Add `--cao-port` to the demo or tutorial now: rejected because it expands scope into tutorial-pack behavior and verification fixtures.
- Make either workflow inherit launcher config dynamically: rejected because both contracts explicitly chose a fixed target.

## Risks / Trade-offs

- [Installed `cao-server` may not honor the requested port] -> Mitigation: require success only at the requested `base_url`, add explicit failure diagnostics, and update tests to exercise non-default port startup.
- [Broader loopback matching could unintentionally widen support beyond current local-service assumptions] -> Mitigation: keep support limited to `localhost` and `127.0.0.1` with explicit ports.
- [Generic demo scripts may still reject valid non-default loopback URLs even after the launcher core changes] -> Mitigation: explicitly include repo-owned non-interactive CAO demo scripts and exploratory helpers in this change.
- [Active docs and issue notes may drift if some still describe fixed-port CAO as current behavior] -> Mitigation: update launcher reference docs, example configs, and the fixed-port issue note in the same change.
- [Future operators may assume the interactive demo or launcher tutorial now support custom ports too] -> Mitigation: explicitly state in proposal, design, specs, and docs that both workflows remain fixed to `127.0.0.1:9889`.

## Migration Plan

1. Update launcher and loopback specs to replace the fixed `:9889` contract with loopback host plus explicit port requirements.
2. Update active generic demo-script specs and helper guidance where local CAO currently means exact `:9889`, while preserving the interactive demo and launcher tutorial fixed-target specs.
3. Implement launcher validation/startup changes so `base_url` drives child-process port selection and health verification.
4. Generalize shared loopback no-proxy helpers and runtime/REST-client call sites to the new supported loopback-with-port contract.
5. Refresh unit/integration tests, repo-owned CAO demo scripts, exploratory helpers, launcher docs, example configs, and the fixed-port issue note.

Rollback strategy:
- Restore the exact `:9889` allowlist in launcher and loopback helpers.
- Remove launch-time selected-port injection from the CAO server environment.
- Revert the doc and issue-note updates that advertise configurable loopback port support.

## Open Questions

- Whether a later follow-up should add `::1` as a third supported loopback host spelling once the repo is ready to own IPv6-specific artifact and documentation behavior.
- Whether the interactive demo should eventually expose a controlled `--cao-port` override once the generic launcher/runtime path has proven stable.

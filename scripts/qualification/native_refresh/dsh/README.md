# DSH Native Refresh Qualification

These development utilities test installed native DSH APIs before Houmao refresh implementation. They create synthetic homes and a local MCP server, use no real provider credentials, and never operate on an existing agent or tmux server. The HMR probes deliberately exercise unsafe behavior inside disposable native contexts. They do not add a product refresh API.

## Run the Native SDK Probes

Select the installed `node_modules` tree explicitly. The utility records native package versions and entry-file SHA-256 hashes. Run from the repository root:

```sh
mkdir -p tmp/native-refresh/dsh
env -u TMUX -u TMUX_PANE node scripts/qualification/native_refresh/dsh/probe.mjs \
  --runtime-node-modules "$PWD/tmp/dsh/npm-runtime/node_modules" \
  --report "$PWD/tmp/native-refresh/dsh/qualification.json"
```

The entrypoint supplies Node's required `--expose-internals` flag to its owned subprocesses. Each subprocess has a 45-second deadline. Every owned worker receives a minimal environment with only PATH, locale and its own temporary HOME/XDG/TMPDIR directories; auth variables, TMUX variables and NODE_OPTIONS are excluded. Its working directory is private. All homes are freshly created under the operating-system temporary directory and removed after the probe. The worker fixture is copied into its own temporary tree so its intentional host-dependency edits cannot affect installed native packages or repository source.

## Run the Controlled Web Probe

The Web utility reuses the repository's controlled native Web factory. Its synthetic provider records requests, and the test requires an empty request list. Native host startup requires explicit selection of the previously qualified `0.2.2-rc.3` executable. No tmux server is needed.

```sh
env -u TMUX -u TMUX_PANE \
  PYTHONPATH="$PWD:$PWD/src" \
  HOUMAO_DSH_EXECUTABLE="$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" \
  HOUMAO_DSH_NODE_MODULES="$PWD/tmp/dsh/npm-runtime/node_modules" \
  HOUMAO_NATIVE_REFRESH_REPORT="$PWD/tmp/native-refresh/dsh/web-qualification.json" \
  pixi run pytest -q scripts/qualification/native_refresh/dsh/test_web_probe.py
```

The fixture starts and cleans up only its captured native host process. Its probe route uses the native host's authenticated connection and exists only in this selected qualification host. The test requires matching selected package versions and checks that the executable and module tree belong to the same installation.

## Executed Findings

On 2026-11-17, the explicit local npm installation reported `0.2.2-rc.3`; Node reported `v26.13.0`. The SDK command passed, and the controlled Web command passed one test. Package hashes are emitted in the JSON report. The separate PATH `dsh` reported `0.2.2-rc.1`; its declarations expose reconciliation methods, but these commands do not qualify that installation.

| Probe | Observed Result | Scope |
| --- | --- | --- |
| Filesystem skill provider, `watch: false` | Add/remove and changed frontmatter remain cached; a subsequent body load reads current bytes. | Native SDK registry/provider. |
| Filesystem skill provider, `watch: true` | Add/update/remove reach the next catalog lookup. | Native SDK registry/provider; no Agent or model request. |
| HMR, `root: []` | Editing a profile patch changes active configuration before an explicit refresh call. | Native profile watches remain active when broad source watching is empty. |
| HMR with changed host dependency and ordinary config | Reconciliation reports pending `host-module` after already stopping/replacing the ordinary config plugin. | A returned restart limitation is not a side-effect-free preflight. |
| HMR replacement failure | The old plugin stops; the replacement throws and stays inactive. | The native result does not establish rollback. |
| Explicit app-boot recomposition with HMR absent | Configuration stays unchanged until explicit reconciliation. | SDK proof of a configuration path without automatic HMR watches. |
| Explicit MCP declaration add/update/remove | Actual registered tools appear, change from `marker_v1` to `marker_v2`, then disappear. | Real local stdio MCP children; removal proves tool withdrawal, not independently verified transport or process closure. |
| Web configuration-only reconciliation | Changed home config, skill add/update/remove, and MCP add/update/remove apply in the existing native Agent. | Same managed identity, process, session ID and journal cursor; zero provider requests; home patch bytes preserved. |

The Web test begins with a fresh native session and makes no model turn. It demonstrates preservation of the native session object and cursor, not behavior of previously loaded skill bodies in conversation history. Its selected host skill provider is explicit and isolated. It does not establish that reloading one provider refreshes every preset-scoped provider or child execution.

## Candidate Explicit Native Recipe

The tested narrow recipe keeps HMR disabled. It reads current `DSH_HOME/cordis.patch.yml` through `readProfilePatches()` and calls `reconcileProfilePatches(ctx.root, patches, ...)` inside the existing Agent's `runMaintenance()`. This avoids `recomposeProfile()`'s package-resolution publication and HMR's module replacement. The test explicitly reloads its selected filesystem provider through the documented native resource `fiber.restart()` API to invalidate a `watch: false` catalog. This restarts only that native resource plugin; the Agent and harness keep their identities.

`Entry.update({}, false, true)` did not invalidate an unchanged provider's catalog in the installed build and is not a substitute for the tested resource reload.

A product adapter still needs to validate affected configuration and protected control/lifecycle entries before mutation, cover every affected native execution and provider, and contain partial/unknown failures. The probes do not establish those safeguards. Native `runMaintenance()` returns to idle in `finally` and can wake queued work, so a failed reload requires explicit containment before native maintenance settles.

`reconcileProfilePatches()` itself can change or stop any entries described by its input. Its use alone is not a control-companion or lifecycle preflight. General package-module refresh remains a separate unqualified capability. HMR exposes no documented manual-only configuration or non-mutating module-preflight method in the inspected build.

## Native Precedence and Source Evidence

The local source reference is `extern/orphan/deepseek-harness` at `39163dd30f703a79079e2d2446545cff3c453738`. Installed packages remain the authority for this execution; source commit identity is not attested by their npm versions.

- `packages/boot/hmr/src/index.ts`: profile watches, `runExclusive()`, `reconcileProfile()` and pending modules.
- `packages/boot/app-boot/src/index.ts`: `reconcileProfilePatches()`, `recomposeProfile()` and configuration activation.
- `packages/boot/app-boot/src/profile-context.ts`: current home/profile reads and retained command-line overlays.
- `packages/skill/skill-filesystem/src/index.ts`: catalog watching and fresh skill-body reads.
- `packages/mcp/mcp-manager/src/index.ts`: asynchronous server reconciliation and retained removed-server status.
- `packages/core/agent-loop/src/agent.ts`: maintenance ownership and final wake behavior.
- `vendor/loader/src/config/entry.ts` and native Cordis Fiber declarations: unchanged entry updates versus explicit resource reload.

The installed rc.3 Cordis API exposes `ctx.root`; the current source checkout uses `ctx[Context.root]`. The probe uses the installed API. Command-line `--patch` files are parsed into launch-time `profileContext.overlays` and are not reread by `readProfilePatches()`. Current home patch files are reread, subject to those retained overlays' native precedence.

No production source, launch profile, current user home or external source checkout is modified by these utilities.

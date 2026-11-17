# Native Agent Home Refresh Preflight

## Status and Scope

Pre-implementation qualification for [issue #82](https://github.com/igamenovoer/houmao/issues/82) and [add-native-agent-home-refresh](../../../openspec/changes/archive/2026-11-17-add-native-agent-home-refresh/proposal.md), executed on 2026-11-17. DSH is the primary target. Kimi Code, Codex, and Claude Code receive best-effort support for verified native behavior.

The probes use disposable native homes, synthetic local MCP servers, and no model prompts or real provider credentials. A successful native control request establishes only the resource behavior actually checked. It does not establish a maintained Houmao transport, conversation-history preservation, or coverage for every native configuration field.

Production refresh implementation has not started. The existing change has 0/30 implementation tasks complete. The planned DSH HMR mechanism needs revision before implementation because its restart-required result can follow destructive native effects.

## Installed Builds and Local References

| Tool | Executed Build | Local Source Reference | Qualification Boundary |
| --- | --- | --- | --- |
| DSH | `0.2.2-rc.3`, explicitly selected from the prior qualified npm runtime | `extern/orphan/deepseek-harness`, commit `39163dd30f703a79079e2d2446545cff3c453738` | The PATH executable reports `0.2.2-rc.1`; its reload behavior is not qualified by the rc.3 tests. |
| Kimi Code | `2.6.0` | `extern/orphan/kimi-code`, commit `67325c1b25e46b2fc66043bceab059221b719fa9` | Local source metadata reports `2.2.0`. Results below come from the installed 2.6.0 server. |
| Codex | `0.169.0` | `extern/orphan/codex`, commit `091008729d5572712ac08964a9602eb71cf31428` | Native app-server tests do not qualify the maintained Houmao headless or interactive controls. |
| Claude Code | `2.1.325` | Installed native binary and its SDK control responses | No complete local first-party Claude Code implementation source was available for this control behavior. |

## Executed Native Behavior

| Tool and Surface | Skills | MCP | Other Configuration | Continuity and Limits |
| --- | --- | --- | --- | --- |
| DSH rc.3 native services and Web | With watching disabled, bodies are read again on load, while add/remove/frontmatter catalogs stay cached. Restarting only the native filesystem-skill provider invalidates that catalog. | Explicit native profile recomposition adds a local stdio server, replaces its advertised tool after a declaration update, and unregisters its tools on removal. | Explicit native profile reconciliation applies changed plugin configuration with HMR disabled. | The Web probe preserves process, session, full managed agent/host identity, and journal cursor under native maintenance, with zero provider requests. Existing model conversation history is untested. |
| Kimi 2.6.0 native server | Session reload discovers added, metadata-edited, and removed skills with watchers disabled. Skill-body consumption is untested. | Session reload reads changed home `mcp.json`; tested add/update/remove and `probe_one` to `probe_two` tool replacement. | A `config.toml` `disable_feedback_survey` edit stays stale before reload and becomes visible after reload. | Same server process and empty-session ID. This is a native server control test, not a test of delivering `/reload` to a managed Houmao TUI. |
| Codex 0.169.0 app-server | `skills/list` with `forceReload: true` discovers add/update/remove. | `config/mcpServer/reload` plus `mcpServerStatus/list` observes server add/rename/remove and changed server tools. | General live configuration reload is unqualified. | Same process and loaded thread IDs. MCP reload affects all loaded threads in that process. |
| Claude Code 2.1.325 SDK stream | `reload_skills` discovers add/update/remove user skills in normal mode. Bare mode omits user skills. | `mcp_reconnect` reloads the implementation/tools of a known server. `reload_plugins` does not reread changed MCP declarations in the tested home or `--mcp-config` file. | General live configuration reload is unqualified. | Same process. Positive reconnect results do not establish generic MCP declaration reload or an owned control stream for a managed Houmao TUI. |

Native MCP removal evidence concerns the agent-visible tool registry. In DSH, the removed server can remain in manager status with `configured: false` and cached `connected` information. Tool absence does not prove that every cached connection or subprocess was destroyed.

Claude's `mcp_set_servers` accepts replacement declarations rather than directly rereading the home. An internal adapter using that setter would need qualified native parsing, precedence, and an owned control stream; the probes establish none of those. The public refresh interface still rejects caller-supplied replacement configuration.

## DSH HMR Design Blocker

The [current design](../../../openspec/changes/archive/2026-11-17-add-native-agent-home-refresh/design.md) proposes enabling HMR with `root: []` and using serialized HMR reconciliation behind native maintenance. Two executed negative probes contradict assumptions needed for that approach:

1. With `root: []`, HMR still watches explicit profile configuration. Editing a patch changed the running plugin before an explicit refresh call. An explicit refresh admission reservation therefore does not govern every reload introduced by enabling that profile.
2. Editing a loaded host dependency and ordinary plugin configuration, then calling `reconcileProfile()`, returned a pending `host-module` result after the ordinary plugin had stopped and its replacement had started. A restart-required decision derived from that result would come after native effects.

A separate failed replacement probe stopped the prior plugin and failed to activate its replacement. The old plugin did not resume automatically. Failure reporting must preserve partial effects and must not claim rollback.

Native automatic discovery is allowed by the user contract. The watcher observation is a coordination and scope risk in the planned HMR integration, rather than a general prohibition on native watchers. The restart-required-after-mutation result is the unresolved conflict with non-destructive preflight.

The relevant native implementation is [HMR initialization and reconciliation](../../../extern/orphan/deepseek-harness/packages/boot/hmr/src/index.ts). There is no public preflight-only reconciliation method or supported switch that disables its configuration watchers while retaining manual reconciliation in the inspected build.

## Candidate DSH Correction

Keep broad HMR disabled and use an explicit native configuration operation under maintenance. Public [app-boot APIs](../../../extern/orphan/deepseek-harness/packages/boot/app-boot/src/index.ts) provide `recomposeProfile()` and `reconcileProfilePatches()`. Native SDK tests establish configuration and MCP add/update/remove through the former. A native Web test establishes configuration updates and skill/MCP add/update/remove through the latter under the bound agent's `runMaintenance()`.

The Web test uses the public native skill-provider `Fiber.restart()` to invalidate the catalog. Only that resource provider restarts; the harness process, native agent, session, incarnations, and journal cursor remain unchanged. Calling `Entry.update()` with unchanged configuration did not invalidate its catalog in the installed build.

The implementation still needs a qualified preflight protecting the host, managed control companion, lifecycle, persistence, and native package mappings. This protection must include service dependencies and nested groups/includes, because replacing an injected service can dispose or rebind an unchanged companion. Changes outside the qualified reload set must report an explicit limitation before mutation. Native package/source replacement must not silently enter this configuration-only operation.

`recomposeProfile()` also has a limitation: it can stop removed entries before rejecting a changed package mapping. It is not itself a non-destructive preflight. `reconcileProfilePatches()` avoids resolution publication, but remains mutating and nontransactional. Native inactive-entry warnings alone do not prove activation; require resource evidence and appropriate required-entry checks.

The Web test edits the actual native `DSH_HOME/cordis.patch.yml`. Native `readProfilePatches()` rereads that file, while launch `--patch` overlays are retained as parsed values in `profileContext.overlays`. A live refresh cannot claim to reread an edited launch-overlay file merely because that file is inside the home. Preserve this native precedence in both implementation and documentation.

An alternative is to retain the broader HMR design and first add an upstream-supported manual mode and preflight API. That adds upstream scope and should be an explicit decision.

Refresh continues to never restart or relaunch. It never reapplies edited Houmao launch profiles or regenerates materialized system prompts.

## Maintained Houmao Control Availability

- DSH ACP preparation currently calls `prepare_dsh_home()` for every invocation. Split launch materialization from current-home loading before advertising next-invocation discovery. The [entrypoint](../../../src/houmao/agents/realm_controller/backends/dsh_acp_entry.py) also passes explicit MCP and model selections, which must preserve qualified current-home precedence.
- Kimi's maintained Houmao headless/TUI surfaces do not yet own the native server endpoint tested here. An upstream endpoint is not sufficient evidence for a managed live adapter.
- Codex's old [app-server backend](../../../src/houmao/agents/realm_controller/backends/codex_app_server.py) is unmaintained and blocked by launch/runtime policy. Do not revive it implicitly to obtain a refresh transport.
- Claude headless execution does not own a bidirectional SDK input stream. Its native SDK controls are useful capability evidence, but do not justify pasting control text into a model prompt or claiming managed live reload support.

Headless next-invocation discovery for these secondary tools remains a separate qualification target. A process-per-turn architecture alone does not establish current-home precedence or every resource's discovery behavior.

## Acceptance Consequences

Implement and qualify DSH first. Investigate all three secondary tools and implement the native paths supported by maintained, owned control surfaces. Record unsupported resources and unqualified versions separately; those limitations must not erase verified skill support or block DSH acceptance.

Do not report aggregate refresh success while current MCP or configuration changes remain pending. Preserve per-resource results, native boundaries, and safe effect evidence. Keep Pi postponed.

## Reproducing the Preflight

The reusable [qualification utilities](../../../scripts/qualification/native_refresh/README.md) accept explicit installed builds and write safe JSON reports. Their READMEs contain the exact executed commands and separate positive observations from untested cases:

- [DSH SDK, HMR-negative, and Web probes](../../../scripts/qualification/native_refresh/dsh/README.md).
- [Kimi native server probe](../../../scripts/qualification/native_refresh/kimi/README.md), with 12 named checks. The same checks also passed with deliberately unusable parent HTTP proxy settings.
- [Codex and Claude control probes](../../../scripts/qualification/native_refresh/codex_claude/README.md).

Source revisions were checked locally with `git rev-parse HEAD`. Ruff formatting/lint and local Markdown-link checks cover the new utilities and report. OpenSpec strict validation passes for the existing change; that validation does not resolve the native HMR design issue or mark implementation tasks complete.

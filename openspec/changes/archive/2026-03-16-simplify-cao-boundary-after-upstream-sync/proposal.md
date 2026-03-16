## Why

Recent upstream `cli-agent-orchestrator` updates removed the old CAO working-directory-under-home restriction and expanded the provider surface with cross-provider profile support plus new providers such as `kimi_cli`. Since this change was created, parts of our repo have already moved forward: the runtime reference and demo overview now mostly describe `cao_only` versus `shadow_only` correctly, and they already treat the default demo worktree as a repo-owned workflow choice rather than a hard CAO requirement.

The remaining drift is now narrower and more concrete:

- the typed CAO response boundary still uses a public closed `CaoProvider` enum even though launch-time mapping already uses plain strings
- shadow parser support is still encoded implicitly in two different places instead of one explicit runtime-owned capability helper
- the launcher and troubleshooting surfaces still repeat the old “workdir must live under home” guidance
- a few demo/help surfaces still need to describe `<launcher-home>/wktree` as an isolation default rather than a CAO rule

## What Changes

- Simplify the repo-owned CAO boundary so terminal `provider` values from CAO responses are treated as forward-compatible non-empty strings instead of a closed public local enum.
- Clarify the CAO-backed runtime contract so `cao_only` remains the generic CAO-native path, while `shadow_only` stays intentionally limited to tools with runtime-owned shadow parsers.
- Add one explicit repo-owned shadow-parser-support helper/capability contract so parsing-mode validation and backend parser-stack selection use the same rule.
- Remove stale documentation and spec guidance that claims CAO workdirs must live under the launcher home tree.
- Reframe interactive demo defaults such as `<launcher-home>/wktree` as isolation and reproducibility choices rather than CAO requirements.
- Preserve explicit runtime-owned provider mapping for the CAO-backed tools we intentionally support today, and continue to fail fast for unsupported runtime tool launches.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Clarify the CAO-backed runtime contract around generic `cao_only`, parser-scoped `shadow_only`, and the absence of a repo-owned home-tree workdir restriction.
- `cao-rest-client-contract`: Make CAO provider parsing forward-compatible while keeping runtime launch-time provider mapping explicit for supported tools.
- `cao-server-launcher`: Clarify that `home_dir` anchors CAO state and process `HOME`, not a repo-owned workdir-containment rule.

## Impact

- Affected code: `src/houmao/cao/models.py`, `src/houmao/cao/__init__.py`, `src/houmao/agents/realm_controller/launch_plan.py`, `src/houmao/agents/realm_controller/backends/cao_rest.py`, and related CAO runtime tests.
- Affected docs: `docs/reference/cao_server_launcher.md`, `docs/reference/cao_shadow_parser_troubleshooting.md`, `src/houmao/demo/cao_interactive_demo/cli.py`, and any remaining demo/operator wording that still implies home-tree containment.
- Affected systems: CAO-backed runtime sessions, typed CAO REST boundary parsing, and the interactive CAO demo/tutorial workflow.
- Dependencies: relies on the synced upstream CAO behavior present in `extern/tracked/cli-agent-orchestrator`.

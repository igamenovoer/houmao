## Why

Recent upstream `cli-agent-orchestrator` updates removed the old CAO working-directory-under-home restriction and expanded the provider surface with cross-provider profile support plus new providers such as `kimi_cli`. Our repository still carries older CAO assumptions in its docs, demo framing, and typed boundary models, which creates needless churn and makes upstream syncs look riskier than they now are.

## What Changes

- Simplify the repo-owned CAO boundary so terminal `provider` values from CAO responses are treated as forward-compatible data instead of a closed local enum list.
- Clarify the CAO-backed runtime contract so `cao_only` remains the generic CAO-native path, while `shadow_only` stays intentionally limited to tools with runtime-owned shadow parsers.
- Remove stale documentation and troubleshooting guidance that claims CAO workdirs must live under the launcher home tree.
- Reframe interactive demo defaults such as `<launcher-home>/wktree` as isolation and reproducibility choices rather than CAO requirements.
- Preserve explicit runtime-owned provider mapping for the CAO-backed tools we intentionally support today, and continue to fail fast for unsupported runtime tool launches.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Clarify the CAO-backed runtime contract around generic `cao_only`, parser-scoped `shadow_only`, and the absence of a repo-owned home-tree workdir restriction.
- `cao-rest-client-contract`: Make CAO provider parsing forward-compatible while keeping runtime launch-time provider mapping explicit for supported tools.

## Impact

- Affected code: `src/houmao/cao/models.py`, `src/houmao/cao/rest_client.py`, `src/houmao/agents/realm_controller/backends/cao_rest.py`, and related CAO runtime tests.
- Affected docs: CAO launcher/reference docs, CAO troubleshooting docs, and interactive demo operator docs/README surfaces.
- Affected systems: CAO-backed runtime sessions, typed CAO REST boundary parsing, and the interactive CAO demo/tutorial workflow.
- Dependencies: relies on the synced upstream CAO behavior present in `extern/tracked/cli-agent-orchestrator`.

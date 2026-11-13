# Managed Agent Usage Qualification

This utility directory supports local qualification of finalized accounting through `houmao-mgr` and `houmao-passive-server`. Disposable homes, credentials, native logs, and public accounting reports belong under `tmp/usage-qualification/`. The committed [provider fixtures](../../../tests/fixtures/agent-usage-records/) contain sanitized accounting and lifecycle evidence.

## Run a Qualification

Start the Qwen endpoint used by the change-local launch aids. The qualified run used `http://127.0.0.1:14888`, model `Qwen/Qwen3.8-27B-FP8`, and fresh homes. Use the [Claude](../../../openspec/changes/expose-agent-usage-records/tests/claude-qwen38.sh), [Codex](../../../openspec/changes/expose-agent-usage-records/tests/codex-qwen38.sh), and [Kimi](../../../openspec/changes/expose-agent-usage-records/tests/kimi-qwen38.sh) aids for raw client captures before managed qualification.

Initialize a disposable project with `houmao-mgr project init`, then create project credentials and specialists with `houmao-mgr project credentials` and `houmao-mgr project specialist create`. Configure the same provider, model, and home selectors as the raw capture. Codex needs the change's Responses configuration projected into its setup; its declared `env_key` must match a projected credential variable. Kimi uses its OpenAI env-model provider with `reasoning_content`, a 262144-token context, and the wrapper's model capabilities. Those `KIMI_MODEL_*` values belong to credential environment material, rather than specialist `--env-set` records.

Launch ordinary managed clients with `houmao-mgr project agents launch --headless` or `--no-headless`. Unattended mode is the project default. TUI qualification opts into `HOUMAO_HOOK_OBSERVATION_CLAUDE=1`, `HOUMAO_HOOK_OBSERVATION_CODEX=1`, or `HOUMAO_HOOK_OBSERVATION_KIMI=1` before launch, so collection can bind an explicit provider session ID. Without a verified identity, usage reports its binding limitation.

Start the maintained server with isolated roots:

```bash
HOUMAO_GLOBAL_RUNTIME_DIR="$scratch/native-runtime" \
HOUMAO_GLOBAL_REGISTRY_DIR="$scratch/registry" \
pixi run houmao-passive-server serve \
  --host 127.0.0.1 --port 19987 \
  --runtime-root "$scratch/server-runtime" \
  --registry-root "$scratch/registry"
```

Use `/houmao/agents/headless/launches` and `/houmao/agents/{agent_ref}/turns` for server-owned headless execution. A manager-launched headless client uses the maintained `/gateway/control/prompt` route. Direct TUI input uses `/gateway/control/send-keys`; send text and `<[Enter]>` separately so a client can finish processing pasted text. See the [managed API reference](../../../docs/reference/managed_agent_api.md) for request bodies.

After each completed turn, compare the public record with its native source:

```bash
pixi run python scripts/qualification/agent-usage/verify_public_usage.py \
  --agent "$agent_name" \
  --expected-records 2 \
  --native-file "$native_file" \
  --output "$scratch/reports/$agent_name.json"
```

The verifier reads the provider's input/output request counters directly and checks public turn identities, deduplication by record ID, and cursor retention after an empty end page. Its output contains public accounting data and numeric comparisons. It excludes native paths, prompts, responses, and credentials. Use it on complete, qualified turns; interrupted turns can retain unknown counters.

## Executed Qualification on 2026-11-13

All runs used the same local Qwen upstream and fresh client homes. Input/output pairs below are public values checked against the corresponding native records. Managed prompts and runtime instructions make these counters differ from the smaller raw-client fixtures.

| Client | Managed Surface | Finalized Completed Turns | Native Input/Output Checks |
| --- | --- | --- | --- |
| Claude Code 2.1.323 | Manager headless, maintained gateway control | 2 resumed turns | 25341/71, 25434/50 |
| Codex 0.167.2 | Passive-server headless launch and turns | 2 resumed turns | 11772/189, 11980/58 |
| Kimi 2.6.0 | Manager headless, maintained gateway control | 2 resumed turns | 17677/266, 18028/54 |
| Claude Code 2.1.323 | Unattended TUI, raw gateway control | 1 turn | 39538/275 |
| Codex 0.167.2 | Unattended TUI, raw gateway control | 2 turns | 12394/119, 12532/85 |
| Kimi 2.6.0 | Unattended TUI, raw gateway control | 1 turn | 20209/246 |

The exact runs retained their empty end cursors. A Codex gateway detach/attach preserved both records, stream ID, and cursor. A passive-server restart preserved the first two Codex records byte-for-byte and recovered the interrupted third record with its original outcome and timing. A subsequent interrupt agreed across turn status and usage, reporting `interrupted`, return code `-15`, and unknown token counters. After explicit stop and another server restart, all four Codex records remained addressable without a controller. Raw provider artifacts and accounting-only reports remain in the ignored `tmp/usage-qualification/api-managed-smoke/` tree.

Qualification cleanup stopped the eight manager-launched clients, three server-managed test authorities, four hook collectors, and the local passive server. The final check found no remaining qualification tmux sessions or service processes. The ignored artifacts remain available for inspection.

The live checks found four defects, now covered by regression tests: a headless record could be reassembled as a second native charge; Claude hook prompt IDs used a different namespace from native user UUIDs; passive turn status read a different artifact directory from execution; and an interrupt could reach the process before passive status persisted the request. Fresh runs above used the corrected implementation. Earlier faulty ledgers remain disposable diagnostic evidence and are excluded from the table.

Semantic TUI prompt submission registers a managed accounting ID before dispatch. The current adapters do not return a verified native turn acknowledgement. The live Codex managed submission therefore remained pending with `managed_native_association_pending`, including after gateway restart; it produced no extra finalized record. Direct native TUI turns remain queryable. Claude hook lifecycle prompt IDs supply no verified mapping to native user UUIDs and cannot create an independent accounting turn. These checks do not qualify private subagent inclusion or undocumented provider billing semantics.

## Automated Regression Coverage

```bash
pixi run python -m pytest \
  tests/integration/agents/realm_controller/test_agent_usage_workflows.py \
  tests/unit/agents/realm_controller/test_usage_api.py \
  tests/unit/passive_server/test_usage.py
```

The integration suite uses exact-client fixtures with the real collector, ledger, gateway route, and passive-server authority route. It checks resumed source selection, failed/interrupted/missing-metric recovery, original generation and wall time, provider reset, attachment during a turn, pending managed association, source replacement, and restart cursor continuity. It uses temporary directories and does not require a provider endpoint.

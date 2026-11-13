# Managed Agent Usage Qualification

Use the [test-fixture helper](../../agents/test-fixtures/README.md) for future raw and managed runs. Tracked [provider captures](../../../tests/fixtures/agent-usage-records/) retain their historical model/version facts. Completed change-local wrappers are reference evidence, rather than launch dependencies.

## Run a Qualification

Select `self-hosted` with a compatible endpoint and an explicit non-Qwen3.8 model, or `cloud-api` with DeepSeek key/base URL references from an explicitly selected ignored env file. Do not put keys in arguments or tracked files. Kimi also requires a qualified context window. Declare Responses for Codex, Chat Completions for Kimi, and Anthropic Messages for Claude.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare --case cloud-api --client codex --model MODEL --env-file .env --mode headless --surface raw
pixi run python scripts/agents/test-fixtures/fixture.py launch --run-dir /external/raw-run --prompt 'Reply exactly OK. Do not use tools.'
pixi run python scripts/agents/test-fixtures/fixture.py prompt --run-dir /external/raw-run --prompt 'Reply exactly DONE. Do not use tools.'
```

Repeat with `--surface manager` for each client in headless and unattended TUI modes. Managed headless prompts use existing gateway control; direct TUI input sends literal text and Enter separately. The helper records authoritative identities and enables selected hook observation for TUI. Start `houmao-passive-server` with external roots for passive headless birth and use `launch --passive-url http://127.0.0.1:PORT`. Passive TUI birth is unsupported.

Capture exact client versions, actual model, completed and resumed turns, routing, and available public usage evidence in sanitized reports. Private homes, env files, raw captures, and native logs stay in the external run. `check --run-dir /external/run --live` reads public usage. `stop --run-dir /external/run` stops only its captured identity. Missing or rejected credentials and unavailable protocols are gaps, never passes.

For an existing passive authority, compare finalized counters independently:

```bash
pixi run python scripts/qualification/agent-usage/verify_public_usage.py --agent ID --expected-records 2 --native-file /external/native-file --output /external/report.json
```

The verifier compares request increments and verifies cursor retention. It exports accounting data and numeric comparisons without prompts, responses, keys, or native source paths. See the [managed API reference](../../../docs/reference/managed_agent_api.md) for route details.

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

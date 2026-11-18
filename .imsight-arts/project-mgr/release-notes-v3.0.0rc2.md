Houmao 3.0.0rc2 adds layered per-tool launch settings and aligns managed DeepSeek Harness configuration with its native provider options.

## Upgrade From 3.0.0rc1

- Move DSH settings from `dsh-setup.yaml` to a setup's `tool-params.yaml` or supply `tool_params` on a specialist or launch profile. Use `model.name` to select a model and replace numbered model reasoning maps with the named `reasoning_efforts` slots.
- Configure the endpoint and API-key roles in existing DSH bundles with `houmao-mgr project credentials dsh set`. Use `env_ref` to bind MCP headers and environment entries to values in the selected private bundle. [DSH Headless Reference](https://igamenovoer.github.io/houmao/reference/run-phase/dsh-headless/)
- Reattach the local gateway after an ACP relaunch to send prompts through the gateway on the new execution generation. [Session Lifecycle](https://igamenovoer.github.io/houmao/reference/run-phase/session-lifecycle/)

## What Changed

- Houmao merges tool defaults, setups, presets or specialists, launch profiles, and one-shot overrides. Managed launch validates the effective settings before stopping a predecessor or changing its runtime state.
- DSH supports OpenAI Chat Completions, OpenAI Responses, Anthropic Messages, and Google Generative AI through pi-ai, alongside the native DeepSeek Messages adapter. Compatible routes can use native model options, named reasoning slots, and retry settings.
- Self-hosted pi-ai Chat Completions can use endpoint-only credentials when the endpoint accepts the fixed public authorization placeholder.
- ACP and Web share an unattended permission preset. Surfaced provider and startup errors retain diagnostic details with credentials redacted.
- Houmao accepts DSH releases and release candidates from `0.2.2-rc.1` onward.

## Install the Candidate

```bash
python -m pip install houmao==3.0.0rc2
npx skills add https://github.com/igamenovoer/houmao-skills#v3.0.0rc2
```

## Qualification

The candidate passed 4,767 unit tests and all 119 DSH integration tests. Fourteen unit tests were skipped. Lint, type checking, the strict docs build, distribution validation, and installed-wheel smoke checks passed.

Endpoint-only ACP and Web prompts completed on DSH `0.2.2-rc.3` against self-hosted SGLang with `Qwen/Qwen3.8-27B-FP8`. ACP sent the expected wire values `none` and `low` for reasoning levels 0 and 1. A controlled HTTP 400 preserved the error detail and redacted all synthetic secrets. [Qualification evidence](https://github.com/igamenovoer/houmao/blob/v3.0.0rc2/context/campaigns/debug/2026-11-18-houmao-3-0-interactive-review/evidences/2026-11-18-dsh-qwen38-endpoint-only-qualification.md)

[Compare v3.0.0rc1 and v3.0.0rc2](https://github.com/igamenovoer/houmao/compare/v3.0.0rc1...v3.0.0rc2)
